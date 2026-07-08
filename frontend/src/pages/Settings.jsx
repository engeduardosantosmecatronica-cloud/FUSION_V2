import React, { useState, useEffect } from 'react';
import { base44 } from '@/api/base44Client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ArrowLeft, Server, Wifi, WifiOff, Save, Loader2, Trash2,
  Download, Terminal, FileCode, Copy, CheckCircle
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

// ── Bridge Python code ───────────────────────────────────────────────
const BRIDGE_PY = `#!/usr/bin/env python3
"""
MT5 Bridge Server — bridge_server.py
Conecta ao MT5 via Named Pipe (Windows) e publica dados via WebSocket.

Instalar dependências:
    pip install fastapi uvicorn websockets aiofiles pydantic

Rodar:
    python bridge_server.py
"""

import asyncio
import json
import time
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

import websockets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Config ──────────────────────────────────────────────────────────
WS_HOST = "localhost"
WS_PORT = 8765
API_PORT = 8766
PIPE_NAME = r"\\\\.\\pipe\\mt5bridge"
DB_PATH = "candles.db"
BUFFER_SIZE = 500  # candles por símbolo/tf em memória

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bridge")

# ── In-memory buffer ─────────────────────────────────────────────────
_buffers = {}   # {("EURUSD","M5"): [candle, ...]}
_last_tick = {} # {"EURUSD": tick}
_connected_ws = set()
_signals = []

def get_buffer(symbol, tf):
    key = (symbol, tf)
    if key not in _buffers:
        _buffers[key] = []
    return _buffers[key]

# ── SQLite ───────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, timeframe TEXT,
            ts INTEGER,  -- Unix ms
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            UNIQUE(symbol, timeframe, ts)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_sym_tf_ts ON candles(symbol, timeframe, ts)")
    con.commit()
    con.close()

def insert_candle(c):
    t0 = time.monotonic()
    con = sqlite3.connect(DB_PATH)
    ts = int(datetime.fromisoformat(c["timestamp"].replace("Z","")).timestamp() * 1000)
    try:
        con.execute(
            "INSERT OR REPLACE INTO candles(symbol,timeframe,ts,open,high,low,close,volume) VALUES(?,?,?,?,?,?,?,?)",
            (c["symbol"], c["timeframe"], ts, c["open"], c["high"], c["low"], c["close"], c.get("volume", 0))
        )
        con.commit()
    finally:
        con.close()
    ms = round((time.monotonic() - t0) * 1000, 1)
    log.info(f"[DB] INSERT {c['symbol']} {c['timeframe']} ts={ts} | {ms}ms")

def query_candles(symbol, tf, limit=200, from_ts=None):
    con = sqlite3.connect(DB_PATH)
    if from_ts:
        rows = con.execute(
            "SELECT ts,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? AND ts>=? ORDER BY ts LIMIT ?",
            (symbol, tf, from_ts, limit)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT ts,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY ts DESC LIMIT ?",
            (symbol, tf, limit)
        ).fetchall()
    con.close()
    result = []
    for r in rows:
        ts_iso = datetime.fromtimestamp(r[0]/1000, tz=timezone.utc).isoformat()
        result.append({"timestamp": ts_iso, "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]})
    return sorted(result, key=lambda x: x["timestamp"])

# ── WebSocket broadcast ───────────────────────────────────────────────
async def broadcast(msg: dict):
    if not _connected_ws:
        return
    data = json.dumps(msg)
    dead = set()
    for ws in _connected_ws.copy():
        try:
            await ws.send(data)
        except Exception:
            dead.add(ws)
    _connected_ws -= dead

# ── Named Pipe reader (Windows) ───────────────────────────────────────
async def read_pipe_loop():
    """Lê mensagens JSON do EA via Named Pipe."""
    import win32pipe, win32file, pywintypes
    log.info(f"[PIPE] Aguardando EA em {PIPE_NAME}...")
    while True:
        try:
            pipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_INBOUND,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                1, 65536, 65536, 0, None
            )
            win32pipe.ConnectNamedPipe(pipe, None)
            log.info("[PIPE] EA conectado!")
            while True:
                try:
                    _, data = win32file.ReadFile(pipe, 65536)
                    msg = json.loads(data.decode("utf-8"))
                    await process_message(msg)
                except Exception as e:
                    log.warning(f"[PIPE] Leitura encerrada: {e}")
                    break
        except Exception as e:
            log.error(f"[PIPE] Erro: {e}")
            await asyncio.sleep(3)

async def process_message(msg):
    t0 = time.monotonic()
    mtype = msg.get("t")

    if mtype == "bar":
        candle = {
            "symbol": msg["s"],
            "timeframe": msg["tf"],
            "open": msg["o"], "high": msg["h"],
            "low": msg["l"],  "close": msg["c"],
            "volume": msg.get("v", 0),
            "timestamp": msg["ts"],
            "closed": msg.get("closed", False),
            "source": "mt5_live"
        }
        buf = get_buffer(msg["s"], msg["tf"])
        if buf and buf[-1]["timestamp"] == candle["timestamp"]:
            buf[-1] = candle  # atualização incremental
        else:
            buf.append(candle)
            if len(buf) > BUFFER_SIZE:
                buf.pop(0)
            if candle["closed"]:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, insert_candle, candle)

        ms = round((time.monotonic() - t0) * 1000, 1)
        log.info(f"[BAR] {msg['s']} {msg['tf']} close={msg['c']} closed={msg.get('closed')} | {ms}ms")
        await broadcast({"type": "candle", "data": candle})

    elif mtype == "tick":
        tick = {"symbol": msg["s"], "bid": msg["b"], "ask": msg["a"],
                "spread": round((msg["a"] - msg["b"]) * 10000, 1),
                "timestamp": msg["ts"]}
        _last_tick[msg["s"]] = tick
        await broadcast({"type": "tick", "data": tick})

# ── WebSocket handler ─────────────────────────────────────────────────
async def ws_handler(ws):
    _connected_ws.add(ws)
    log.info(f"[WS] Cliente conectado. Total: {len(_connected_ws)}")
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await ws.send(json.dumps({"type": "pong", "ts": msg.get("ts")}))
            except Exception:
                pass
    finally:
        _connected_ws.discard(ws)
        log.info(f"[WS] Cliente desconectado. Total: {len(_connected_ws)}")

# ── FastAPI REST ──────────────────────────────────────────────────────
app = FastAPI(title="MT5 Bridge API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/candles")
def get_candles(symbol: str, tf: str, limit: int = 200, from_ts: int = None):
    t0 = time.monotonic()
    # Primeiro tenta buffer em memória
    buf = get_buffer(symbol, tf)
    if buf:
        result = buf[-limit:]
        ms = round((time.monotonic() - t0) * 1000, 1)
        log.info(f"[REST] /candles {symbol} {tf} from_memory={len(result)} | {ms}ms")
        return result
    # Fallback: SQLite
    result = query_candles(symbol, tf, limit, from_ts)
    ms = round((time.monotonic() - t0) * 1000, 1)
    log.info(f"[REST] /candles {symbol} {tf} from_db={len(result)} | {ms}ms")
    return result

@app.get("/api/status")
def get_status():
    return {
        "ws_clients": len(_connected_ws),
        "symbols": list(set(k[0] for k in _buffers)),
        "timeframes": list(set(k[1] for k in _buffers)),
        "last_ticks": list(_last_tick.keys()),
    }

@app.get("/api/signals")
def get_signals(symbol: str = None, limit: int = 50):
    result = [s for s in _signals if not symbol or s.get("symbol") == symbol]
    return result[:limit]

# ── Main ──────────────────────────────────────────────────────────────
async def main():
    init_db()
    log.info("=== MT5 Bridge Server iniciado ===")
    ws_server = websockets.serve(ws_handler, WS_HOST, WS_PORT)
    api_config = uvicorn.Config(app, host="0.0.0.0", port=API_PORT, log_level="warning")
    api_server = uvicorn.Server(api_config)

    await asyncio.gather(
        ws_server,
        api_server.serve(),
        read_pipe_loop(),
    )

if __name__ == "__main__":
    asyncio.run(main())
`;

// ── MQL5 EA code ─────────────────────────────────────────────────────
const EA_MQ5 = `//+------------------------------------------------------------------+
//| MT5Bridge.mq5 — Expert Advisor para enviar dados ao bridge      |
//| Instalar em: MQL5/Experts/MT5Bridge.mq5                         |
//+------------------------------------------------------------------+
#property copyright "MT5 Bridge"
#property version   "1.00"
#property strict

input string   Symbol_Filter = "";      // Deixe vazio para símbolo do gráfico
input string   Timeframe_Send = "M5";   // Timeframe a enviar
input bool     Send_Ticks     = true;   // Enviar ticks?
input bool     Send_Candles   = true;   // Enviar candles?
input string   Pipe_Name      = "\\\\\\\\.\\\\pipe\\\\mt5bridge";

int    pipe_handle = INVALID_HANDLE;
string sym;
ENUM_TIMEFRAMES tf;
datetime last_bar_time = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   sym = Symbol_Filter == "" ? _Symbol : Symbol_Filter;
   tf  = StringToTF(Timeframe_Send);

   // Tenta abrir Named Pipe
   pipe_handle = FileOpen(Pipe_Name, FILE_WRITE | FILE_BIN | FILE_SHARE_READ);
   if(pipe_handle == INVALID_HANDLE) {
      Print("[Bridge] AVISO: Pipe não encontrado. Inicie bridge_server.py primeiro.");
   } else {
      Print("[Bridge] Conectado ao pipe: ", Pipe_Name);
   }

   EventSetMillisecondTimer(100);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   if(pipe_handle != INVALID_HANDLE) FileClose(pipe_handle);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!Send_Ticks) return;

   MqlTick tick;
   if(!SymbolInfoTick(sym, tick)) return;

   string ts = TimeToISO(tick.time);
   string msg = StringFormat(
      "{\\\"t\\\":\\\"tick\\\",\\\"s\\\":\\\"%s\\\",\\\"b\\\":%.5f,\\\"a\\\":%.5f,\\\"ts\\\":\\\"%s\\\"}\\n",
      sym, tick.bid, tick.ask, ts
   );
   SendToPipe(msg);
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(!Send_Candles) return;

   datetime bar_time = iTime(sym, tf, 0);
   if(bar_time == 0) return;

   double o = iOpen(sym, tf, 0);
   double h = iHigh(sym, tf, 0);
   double l = iLow(sym, tf, 0);
   double c = iClose(sym, tf, 0);
   long   v = iVolume(sym, tf, 0);
   string ts = TimeToISO((datetime)bar_time);
   bool closed = (bar_time != last_bar_time && last_bar_time != 0);

   if(closed) {
      // Envia candle anterior (fechado)
      double co = iOpen(sym, tf, 1);
      double ch = iHigh(sym, tf, 1);
      double cl = iLow(sym, tf, 1);
      double cc = iClose(sym, tf, 1);
      long   cv = iVolume(sym, tf, 1);
      string cts = TimeToISO(iTime(sym, tf, 1));
      SendCandle(co, ch, cl, cc, cv, cts, true);
      last_bar_time = bar_time;
   }

   // Sempre envia candle atual (parcial)
   SendCandle(o, h, l, c, v, ts, false);
}

//+------------------------------------------------------------------+
void SendCandle(double o, double h, double l, double c, long v, string ts, bool closed)
{
   string msg = StringFormat(
      "{\\\"t\\\":\\\"bar\\\",\\\"s\\\":\\\"%s\\\",\\\"tf\\\":\\\"%s\\\",\\\"o\\\":%.5f,\\\"h\\\":%.5f,\\\"l\\\":%.5f,\\\"c\\\":%.5f,\\\"v\\\":%d,\\\"ts\\\":\\\"%s\\\",\\\"closed\\\":%s}\\n",
      sym, Timeframe_Send, o, h, l, c, (int)v, ts, closed ? "true" : "false"
   );
   SendToPipe(msg);
}

//+------------------------------------------------------------------+
void SendToPipe(string msg)
{
   if(pipe_handle == INVALID_HANDLE) {
      // Tenta reconectar
      pipe_handle = FileOpen(Pipe_Name, FILE_WRITE | FILE_BIN | FILE_SHARE_READ);
      if(pipe_handle == INVALID_HANDLE) return;
   }
   uchar buf[];
   StringToCharArray(msg, buf, 0, StringLen(msg));
   FileWriteArray(pipe_handle, buf, 0, ArraySize(buf));
   FileFlush(pipe_handle);
}

//+------------------------------------------------------------------+
string TimeToISO(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
      dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec);
}

//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTF(string s)
{
   if(s == "M1")  return PERIOD_M1;
   if(s == "M5")  return PERIOD_M5;
   if(s == "M15") return PERIOD_M15;
   if(s == "M30") return PERIOD_M30;
   if(s == "H1")  return PERIOD_H1;
   if(s == "H4")  return PERIOD_H4;
   if(s == "D1")  return PERIOD_D1;
   return PERIOD_M5;
}
`;

// ── Requirements.txt ─────────────────────────────────────────────────
const REQUIREMENTS = `fastapi==0.115.0
uvicorn[standard]==0.30.0
websockets==13.0
aiofiles==23.2.1
pydantic==2.8.0
pywin32==306
`;

export default function Settings() {
  const queryClient = useQueryClient();
  const [server, setServer] = useState('');
  const [accountId, setAccountId] = useState('');
  const [balance, setBalance] = useState('');
  const [equity, setEquity] = useState('');
  const [margin, setMargin] = useState('');
  const [freeMargin, setFreeMargin] = useState('');
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState('');

  const { data: connections = [] } = useQuery({
    queryKey: ['connections'],
    queryFn: () => base44.entities.MT5Connection.list('-created_date', 1),
  });

  const connection = connections[0];

  useEffect(() => {
    if (connection) {
      setServer(connection.server || '');
      setAccountId(connection.account_id || '');
      setBalance(connection.balance?.toString() || '');
      setEquity(connection.equity?.toString() || '');
      setMargin(connection.margin?.toString() || '');
      setFreeMargin(connection.free_margin?.toString() || '');
    }
  }, [connection]);

  const handleSave = async () => {
    setSaving(true);
    const data = {
      server, account_id: accountId, status: 'connected',
      balance: parseFloat(balance) || 0,
      equity: parseFloat(equity) || 0,
      margin: parseFloat(margin) || 0,
      free_margin: parseFloat(freeMargin) || 0,
      last_sync: new Date().toISOString(),
    };
    if (connection) {
      await base44.entities.MT5Connection.update(connection.id, data);
    } else {
      await base44.entities.MT5Connection.create(data);
    }
    queryClient.invalidateQueries({ queryKey: ['connections'] });
    setSaving(false);
  };

  const handleClearData = async () => {
    if (!confirm('Limpar todos os candles?')) return;
    const items = await base44.entities.Candle.list('created_date', 500);
    await Promise.all(items.map(c => base44.entities.Candle.delete(c.id)));
    queryClient.invalidateQueries({ queryKey: ['candles'] });
  };

  const handleDownload = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = (content, key) => {
    navigator.clipboard.writeText(content);
    setCopied(key);
    setTimeout(() => setCopied(''), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-4">
      <div className="max-w-3xl mx-auto space-y-4">

        {/* Header */}
        <div className="flex items-center gap-3 py-2">
          <Link to="/"><Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground"><ArrowLeft className="w-4 h-4" /></Button></Link>
          <div>
            <h1 className="text-lg font-bold">Configurações</h1>
            <p className="text-xs text-muted-foreground">Conexão MT5, dados e arquivos do bridge</p>
          </div>
        </div>

        <Tabs defaultValue="connection">
          <TabsList className="bg-[#161b22] border border-[#1c2333]">
            <TabsTrigger value="connection" className="text-xs">Conexão MT5</TabsTrigger>
            <TabsTrigger value="bridge" className="text-xs">Bridge Python</TabsTrigger>
            <TabsTrigger value="ea" className="text-xs">Expert Advisor MQL5</TabsTrigger>
            <TabsTrigger value="data" className="text-xs">Dados</TabsTrigger>
          </TabsList>

          {/* ── Connection ── */}
          <TabsContent value="connection">
            <Card className="bg-[#161b22] border-[#1c2333]">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Server className="w-4 h-4 text-blue-400" />
                    <CardTitle className="text-sm">Conta MT5</CardTitle>
                  </div>
                  {connection && (
                    <Badge className={cn('text-xs', connection.status === 'connected' ? 'bg-green-600/20 text-green-400 border-green-600/30' : 'bg-red-600/20 text-red-400 border-red-600/30')}>
                      {connection.status === 'connected' ? <Wifi className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
                      {connection.status}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1"><Label className="text-xs text-muted-foreground">Servidor</Label>
                    <Input value={server} onChange={e => setServer(e.target.value)} placeholder="MetaQuotes-Demo" className="h-8 text-xs bg-[#0d1117] border-[#1c2333]" /></div>
                  <div className="space-y-1"><Label className="text-xs text-muted-foreground">Conta</Label>
                    <Input value={accountId} onChange={e => setAccountId(e.target.value)} placeholder="12345678" className="h-8 text-xs font-mono bg-[#0d1117] border-[#1c2333]" /></div>
                  <div className="space-y-1"><Label className="text-xs text-muted-foreground">Saldo ($)</Label>
                    <Input type="number" value={balance} onChange={e => setBalance(e.target.value)} placeholder="10000" className="h-8 text-xs font-mono bg-[#0d1117] border-[#1c2333]" /></div>
                  <div className="space-y-1"><Label className="text-xs text-muted-foreground">Patrimônio ($)</Label>
                    <Input type="number" value={equity} onChange={e => setEquity(e.target.value)} placeholder="10000" className="h-8 text-xs font-mono bg-[#0d1117] border-[#1c2333]" /></div>
                  <div className="space-y-1"><Label className="text-xs text-muted-foreground">Margem ($)</Label>
                    <Input type="number" value={margin} onChange={e => setMargin(e.target.value)} placeholder="0" className="h-8 text-xs font-mono bg-[#0d1117] border-[#1c2333]" /></div>
                  <div className="space-y-1"><Label className="text-xs text-muted-foreground">Margem Livre ($)</Label>
                    <Input type="number" value={freeMargin} onChange={e => setFreeMargin(e.target.value)} placeholder="10000" className="h-8 text-xs font-mono bg-[#0d1117] border-[#1c2333]" /></div>
                </div>
                <Button onClick={handleSave} disabled={saving} className="w-full h-8 text-xs">
                  {saving ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Save className="w-3.5 h-3.5 mr-2" />}
                  Salvar
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Bridge Python ── */}
          <TabsContent value="bridge">
            <Card className="bg-[#161b22] border-[#1c2333]">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-green-400" />
                    <CardTitle className="text-sm">bridge_server.py</CardTitle>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="h-7 text-xs border-[#1c2333]"
                      onClick={() => handleCopy(REQUIREMENTS, 'req')}>
                      {copied === 'req' ? <CheckCircle className="w-3 h-3 mr-1 text-green-400" /> : <Copy className="w-3 h-3 mr-1" />}
                      requirements.txt
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs border-[#1c2333]"
                      onClick={() => handleDownload(BRIDGE_PY, 'bridge_server.py')}>
                      <Download className="w-3 h-3 mr-1" /> Download
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs border-[#1c2333]"
                      onClick={() => handleCopy(BRIDGE_PY, 'bridge')}>
                      {copied === 'bridge' ? <CheckCircle className="w-3 h-3 mr-1 text-green-400" /> : <Copy className="w-3 h-3 mr-1" />}
                      Copiar
                    </Button>
                  </div>
                </div>
                <CardDescription className="text-xs space-y-1">
                  <p>1. Salve <code className="bg-muted px-1 rounded">bridge_server.py</code> em qualquer pasta</p>
                  <p>2. Instale dependências: <code className="bg-muted px-1 rounded">pip install fastapi uvicorn websockets pywin32</code></p>
                  <p>3. Execute: <code className="bg-muted px-1 rounded">python bridge_server.py</code></p>
                  <p>4. Adicione o EA MT5Bridge.mq5 ao MetaTrader 5</p>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-80">
                  <pre className="text-[10px] font-mono text-[#c9d1d9] whitespace-pre-wrap leading-relaxed">{BRIDGE_PY}</pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── EA MQL5 ── */}
          <TabsContent value="ea">
            <Card className="bg-[#161b22] border-[#1c2333]">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-yellow-400" />
                    <CardTitle className="text-sm">MT5Bridge.mq5</CardTitle>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="h-7 text-xs border-[#1c2333]"
                      onClick={() => handleDownload(EA_MQ5, 'MT5Bridge.mq5')}>
                      <Download className="w-3 h-3 mr-1" /> Download
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs border-[#1c2333]"
                      onClick={() => handleCopy(EA_MQ5, 'ea')}>
                      {copied === 'ea' ? <CheckCircle className="w-3 h-3 mr-1 text-green-400" /> : <Copy className="w-3 h-3 mr-1" />}
                      Copiar
                    </Button>
                  </div>
                </div>
                <CardDescription className="text-xs space-y-1">
                  <p>1. Copie <code className="bg-muted px-1 rounded">MT5Bridge.mq5</code> para <code className="bg-muted px-1 rounded">MQL5/Experts/</code> no seu terminal MT5</p>
                  <p>2. Compile no MetaEditor (F7)</p>
                  <p>3. Arraste o EA para o gráfico do ativo desejado</p>
                  <p>4. Certifique que o bridge_server.py está rodando antes</p>
                  <p>5. Habilite "Allow DLL imports" nas propriedades do EA</p>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-80">
                  <pre className="text-[10px] font-mono text-[#c9d1d9] whitespace-pre-wrap leading-relaxed">{EA_MQ5}</pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Data ── */}
          <TabsContent value="data">
            <Card className="bg-[#161b22] border-[#1c2333]">
              <CardHeader>
                <CardTitle className="text-sm">Gerenciar Dados</CardTitle>
                <CardDescription className="text-xs">Candles armazenados no banco local da plataforma</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="destructive" onClick={handleClearData} className="text-xs h-8">
                  <Trash2 className="w-3.5 h-3.5 mr-2" />
                  Limpar Todos os Candles
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
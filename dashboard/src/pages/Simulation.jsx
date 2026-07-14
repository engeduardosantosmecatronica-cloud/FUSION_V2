import React, { useState, useRef, useEffect } from "react";
import { generateCandles } from "@/lib/mockData";
import { Button } from "@/components/ui/button";
import { Play, Pause, RotateCcw, FastForward, ShoppingCart, ArrowDownCircle } from "lucide-react";

export default function Simulation() {
  const allCandles = useRef(generateCandles(200));
  const [visibleCount, setVisibleCount] = useState(30);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [balance, setBalance] = useState(100000);
  const [position, setPosition] = useState(null);
  const [trades, setTrades] = useState([]);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (playing && visibleCount < allCandles.current.length) {
      intervalRef.current = setInterval(() => {
        setVisibleCount(c => {
          if (c >= allCandles.current.length) { setPlaying(false); return c; }
          return c + 1;
        });
      }, 1000 / speed);
    }
    return () => clearInterval(intervalRef.current);
  }, [playing, speed]);

  const candles = allCandles.current.slice(0, visibleCount);
  const current = candles[candles.length - 1];

  function openPosition(side) {
    if (position) return;
    setPosition({ side, entry: current.close, time: visibleCount });
  }

  function closePosition() {
    if (!position) return;
    const pnl = position.side === "BUY" ? current.close - position.entry : position.entry - current.close;
    setBalance(b => b + pnl);
    setTrades(t => [...t, { ...position, exit: current.close, pnl }]);
    setPosition(null);
  }

  function reset() {
    setVisibleCount(30);
    setPlaying(false);
    setBalance(100000);
    setPosition(null);
    setTrades([]);
  }

  const unrealizedPnl = position ? (position.side === "BUY" ? current.close - position.entry : position.entry - current.close) : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Simulação & Replay</h1>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Button size="sm" variant="ghost" className="text-white" onClick={() => setPlaying(!playing)}>
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </Button>
            <Button size="sm" variant="ghost" className="text-white" onClick={reset}><RotateCcw className="w-4 h-4" /></Button>
            <div className="flex gap-1 ml-2">
              {[1, 2, 5, 10].map(s => (
                <button key={s} onClick={() => setSpeed(s)} className={`px-2 py-0.5 rounded text-xs font-medium ${speed === s ? "bg-emerald-500 text-white" : "bg-[#1a2035] text-gray-400"}`}>{s}x</button>
              ))}
            </div>
          </div>
          <span className="text-xs text-gray-500">Candle {visibleCount} / {allCandles.current.length}</span>
        </div>

        {/* Mini chart */}
        <div className="flex items-end gap-0.5 h-48 bg-[#1a2035] rounded-lg p-2 overflow-hidden">
          {candles.slice(-80).map((c, i) => {
            const min = Math.min(...candles.slice(-80).map(x => x.low));
            const max = Math.max(...candles.slice(-80).map(x => x.high));
            const range = max - min || 1;
            const bodyBot = ((Math.min(c.open, c.close) - min) / range) * 100;
            const bodyH = (Math.abs(c.close - c.open) / range) * 100 || 0.5;
            const bullish = c.close >= c.open;
            return (
              <div key={i} className="flex-1 min-w-[2px] relative h-full flex items-end">
                <div className={`w-full rounded-sm ${bullish ? "bg-emerald-500" : "bg-red-500"}`} style={{ height: `${Math.max(bodyH, 1)}%`, marginBottom: `${bodyBot}%` }} />
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between mt-4">
          <div className="text-sm">
            <span className="text-gray-500">Preço: </span>
            <span className="text-white font-bold">{current?.close?.toLocaleString("pt-BR")}</span>
          </div>
          <div className="flex gap-2">
            <Button size="sm" className="bg-emerald-500 hover:bg-emerald-600 text-white" onClick={() => openPosition("BUY")} disabled={!!position}>
              <ShoppingCart className="w-4 h-4 mr-1" /> Comprar
            </Button>
            <Button size="sm" className="bg-red-500 hover:bg-red-600 text-white" onClick={() => openPosition("SELL")} disabled={!!position}>
              <ArrowDownCircle className="w-4 h-4 mr-1" /> Vender
            </Button>
            {position && (
              <Button size="sm" variant="outline" className="border-amber-500/50 text-amber-400" onClick={closePosition}>Fechar</Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500">Saldo</p>
          <p className="text-lg font-bold text-white">R$ {balance.toFixed(0)}</p>
        </div>
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500">Posição</p>
          <p className={`text-lg font-bold ${position ? (position.side === "BUY" ? "text-emerald-400" : "text-red-400") : "text-gray-600"}`}>
            {position ? `${position.side} @ ${position.entry}` : "Nenhuma"}
          </p>
        </div>
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500">P&L Aberto</p>
          <p className={`text-lg font-bold ${unrealizedPnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>{unrealizedPnl.toFixed(0)}</p>
        </div>
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500">Trades</p>
          <p className="text-lg font-bold text-blue-400">{trades.length}</p>
        </div>
      </div>

      {trades.length > 0 && (
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Histórico da Simulação</h2>
          <div className="space-y-1">
            {trades.map((t, i) => (
              <div key={i} className="flex items-center justify-between py-1.5 border-b border-[#1e2740]/30">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${t.side === "BUY" ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"}`}>{t.side}</span>
                  <span className="text-sm text-gray-400">{t.entry} → {t.exit}</span>
                </div>
                <span className={`text-sm font-semibold ${t.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>{t.pnl >= 0 ? "+" : ""}{t.pnl.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
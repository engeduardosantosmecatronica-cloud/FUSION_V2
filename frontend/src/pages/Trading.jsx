import React, { useState, useEffect, useCallback } from 'react';
import { base44 } from '@/api/base44Client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Settings, Database, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

// Chart
import CandleChart from '@/components/chart/CandleChart';
import IndicatorConfig from '@/components/chart/IndicatorConfig';

// Trading panels
import FeedStatus from '@/components/trading/FeedStatus';
import SignalPanel from '@/components/trading/SignalPanel';
import RiskConfig from '@/components/trading/RiskConfig';
import StrategyLog from '@/components/trading/StrategyLog';
import AssetList from '@/components/trading/AssetList';
import TimeframeSelector from '@/components/trading/TimeframeSelector';
import OpenPositions from '@/components/trading/OpenPositions';
import TradeHistory from '@/components/trading/TradeHistory';
import MT5DataImporter from '@/components/trading/MT5DataImporter';
import FusionSignalCard from '@/components/trading/FusionSignalCard';

// Hooks
import { useWebSocket } from '@/hooks/useWebSocket';
import { useCandleBuffer } from '@/hooks/useCandleBuffer';
import { useIndicators } from '@/hooks/useIndicators';

const DEFAULT_INDICATOR_CONFIG = {
  showEMA1: true, ema1Period: 9,
  showEMA2: true, ema2Period: 21,
  showEMA3: false, ema3Period: 50,
  showBoll: false, bollPeriod: 20,
  showRSI: true, rsiPeriod: 14,
  showMACD: false,
};

function addLog(logs, level, message, ms) {
  const entry = { ts: new Date().toISOString(), level, message, ...(ms !== undefined ? { ms } : {}) };
  return [entry, ...logs].slice(0, 200);
}

export default function Trading() {
  const [symbol, setSymbol] = useState('EURUSD');
  const [timeframe, setTimeframe] = useState('M5');
  const [indicatorConfig, setIndicatorConfig] = useState(DEFAULT_INDICATOR_CONFIG);
  const [riskConfig, setRiskConfig] = useState(null);
  const [signals, setSignals] = useState([]);
  const [logs, setLogs] = useState([{ ts: new Date().toISOString(), level: 'info', message: 'Plataforma iniciada. Aguardando dados...' }]);
  const [currentTick, setCurrentTick] = useState(null);
  const [lastPrices, setLastPrices] = useState({});
  const [feedMode, setFeedMode] = useState('demo'); // 'live' | 'demo'
  const [activeTab, setActiveTab] = useState('signal');
  const [bottomTab, setBottomTab] = useState('positions');

  const queryClient = useQueryClient();
  const { load, updateLast, getAll, getLast, version } = useCandleBuffer();
  const log = useCallback((level, message, ms) => setLogs(prev => addLog(prev, level, message, ms)), []);

  // ── WebSocket (bridge local) ──────────────────────────────────────
  const handleWsMessage = useCallback((msg) => {
    const t0 = Date.now();
    if (msg.type === 'candle') {
      const c = msg.data;
      if (c.symbol === symbol && c.timeframe === timeframe) {
        updateLast(c);
        if (c.closed) {
          log('data', `Candle fechado ${c.symbol} ${c.timeframe} | close=${c.close}`, Date.now() - t0);
          queryClient.invalidateQueries({ queryKey: ['candles', symbol, timeframe] });
        }
      }
    } else if (msg.type === 'tick') {
      const tk = msg.data;
      if (tk.symbol === symbol) setCurrentTick(tk);
      setLastPrices(prev => ({
        ...prev,
        [tk.symbol]: { price: tk.bid, change: ((tk.bid - (prev[tk.symbol]?.price || tk.bid)) / (prev[tk.symbol]?.price || tk.bid)) * 100 }
      }));
    } else if (msg.type === 'signal') {
      setSignals(prev => [msg.data, ...prev].slice(0, 50));
      log('signal', `Sinal ${msg.data.signal} (${Math.round((msg.data.confidence || 0) * 100)}%) - ${msg.data.reason}`, Date.now() - t0);
    } else if (msg.type === 'status') {
      log('info', `Status bridge: ${JSON.stringify(msg.data)}`);
    }
  }, [symbol, timeframe, updateLast, log, queryClient]);

  const handleWsStatusChange = useCallback((status) => {
    const msgs = { connected: ['success', 'WebSocket bridge conectado'], disconnected: ['warn', 'Bridge desconectado — tentando reconectar...'], error: ['error', 'Erro de conexão WebSocket'], connecting: ['info', 'Conectando ao bridge local...'] };
    const [level, message] = msgs[status] || ['info', status];
    log(level, message);
    if (status === 'connected') setFeedMode('live');
    if (status === 'disconnected' || status === 'error') setFeedMode('demo');
  }, [log]);

  const { status: wsStatus, latency } = useWebSocket('ws://localhost:8765', {
    onMessage: handleWsMessage,
    onStatusChange: handleWsStatusChange,
  });

  // ── REST: histórico de candles ────────────────────────────────────
  const { data: dbCandles = [], isFetching } = useQuery({
    queryKey: ['candles', symbol, timeframe],
    queryFn: async () => {
      const t0 = Date.now();
      const result = await base44.entities.Candle.filter({ symbol, timeframe }, 'timestamp', 200);
      log('data', `Histórico carregado: ${result.length} candles`, Date.now() - t0);
      return result;
    },
    staleTime: 30000,
  });

  const { data: trades = [] } = useQuery({
    queryKey: ['trades'],
    queryFn: () => base44.entities.Trade.list('-created_date', 50),
  });

  const { data: connections = [] } = useQuery({
    queryKey: ['connections'],
    queryFn: () => base44.entities.MT5Connection.list('-created_date', 1),
  });

  // Load buffer when DB candles arrive
  useEffect(() => {
    if (dbCandles.length > 0) {
      load(dbCandles);
      log('info', `Buffer atualizado: ${dbCandles.length} candles em memória`);
    }
  }, [dbCandles, load]);

  // Clear buffer and reload when symbol/timeframe changes
  useEffect(() => {
    load([]);
    setCurrentTick(null);
    setSignals([]);
    log('info', `Trocando para ${symbol} ${timeframe}...`);
  }, [symbol, timeframe]);

  // Real-time subscriptions from DB
  useEffect(() => {
    const unsub = base44.entities.Candle.subscribe((event) => {
      if (event.data?.symbol === symbol && event.data?.timeframe === timeframe) {
        queryClient.invalidateQueries({ queryKey: ['candles', symbol, timeframe] });
      }
    });
    const unsubTrades = base44.entities.Trade.subscribe(() => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    });
    return () => { unsub(); unsubTrades(); };
  }, [symbol, timeframe, queryClient]);

  // Derived
  const allCandles = getAll();
  const lastCandle = getLast();
  const connection = connections[0];
  const currentPrice = currentTick?.bid || lastCandle?.close || 0;
  const dec = currentPrice > 1000 ? 2 : currentPrice > 100 ? 3 : 5;

  // Indicators (memoized, uses RAF internally)
  const indicators = useIndicators(allCandles, indicatorConfig);

  const handleDataImported = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['candles', symbol, timeframe] });
    log('success', 'Dados importados com sucesso');
  }, [symbol, timeframe, queryClient, log]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['candles', symbol, timeframe] });
  };

  return (
    <div className="h-screen flex flex-col bg-[#0d1117] overflow-hidden text-sm">

      {/* ── TOP BAR ── */}
      <div className="flex items-center justify-between border-b border-[#1c2333] bg-[#161b22] px-0 h-10 shrink-0">
        <div className="flex items-center h-full">
          {/* Logo */}
          <div className="flex items-center gap-2 px-4 h-full border-r border-[#1c2333]">
            <div className="w-6 h-6 rounded bg-blue-600 flex items-center justify-center">
              <span className="text-[9px] font-black text-white">MT</span>
            </div>
            <span className="text-sm font-bold tracking-tight text-white hidden sm:block">TradeView</span>
          </div>

          {/* Symbol selector */}
          <div className="flex items-center gap-1 px-3 h-full border-r border-[#1c2333]">
            <select
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              className="bg-transparent text-sm font-mono font-semibold text-white border-none outline-none cursor-pointer"
            >
              {['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','XAUUSD','BTCUSD','ETHUSD','US500','NAS100','US30'].map(s => (
                <option key={s} value={s} className="bg-[#161b22]">{s}</option>
              ))}
            </select>
          </div>

          {/* Price display */}
          <div className="flex items-center gap-3 px-4 h-full">
            <span className={cn('text-lg font-mono font-bold', lastCandle?.close >= lastCandle?.open ? 'text-[#26a69a]' : 'text-[#ef5350]')}>
              {currentPrice ? currentPrice.toFixed(dec) : '—'}
            </span>
            {lastCandle && (
              <span className={cn('text-xs font-mono', lastCandle.close >= lastCandle.open ? 'text-[#26a69a]' : 'text-[#ef5350]')}>
                {lastCandle.close >= lastCandle.open ? '▲' : '▼'}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 px-2 h-full">
          <MT5DataImporter symbol={symbol} timeframe={timeframe} onImported={handleDataImported} />
          <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={cn('w-3.5 h-3.5', isFetching && 'animate-spin')} />
          </Button>
          <Link to="/settings">
            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground">
              <Settings className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </div>
      </div>

      {/* ── TIMEFRAME + FEED STATUS ── */}
      <div className="flex items-center justify-between border-b border-[#1c2333] bg-[#161b22]/50 shrink-0">
        <TimeframeSelector selected={timeframe} onChange={setTimeframe} />
        <div className="flex items-center gap-2 pr-3">
          <IndicatorConfig config={indicatorConfig} onChange={setIndicatorConfig} />
        </div>
      </div>
      <FeedStatus wsStatus={wsStatus} latency={latency} feedMode={feedMode} candleCount={allCandles.length} />

      {/* ── MAIN LAYOUT ── */}
      <div className="flex-1 flex overflow-hidden min-h-0">

        {/* LEFT SIDEBAR — Asset list */}
        <div className="w-44 shrink-0 border-r border-[#1c2333] bg-[#161b22] hidden xl:flex flex-col">
          <AssetList selected={symbol} onChange={setSymbol} lastPrices={lastPrices} />
        </div>

        {/* CENTER — Chart */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Chart */}
          <div className="flex-1 min-h-0">
            <CandleChart
              candles={allCandles}
              indicators={indicators}
              currentTick={currentTick}
            />
          </div>

          {/* BOTTOM PANEL */}
          <div className="h-40 shrink-0 border-t border-[#1c2333] bg-[#161b22]">
            <div className="flex border-b border-[#1c2333]">
              {[
                { id: 'positions', label: 'Posições' },
                { id: 'history', label: 'Histórico' },
                { id: 'log', label: 'Log' },
              ].map(tab => (
                <button key={tab.id} onClick={() => setBottomTab(tab.id)}
                  className={cn('px-4 py-1.5 text-[11px] font-medium border-b-2 transition-colors',
                    bottomTab === tab.id
                      ? 'border-blue-500 text-white'
                      : 'border-transparent text-[#6e7681] hover:text-white'
                  )}>
                  {tab.label}
                </button>
              ))}
            </div>
            <ScrollArea className="h-[calc(100%-28px)]">
              {bottomTab === 'positions' && <OpenPositions trades={trades} currentPrice={currentPrice} />}
              {bottomTab === 'history' && <TradeHistory trades={trades} />}
              {bottomTab === 'log' && <StrategyLog logs={logs} />}
            </ScrollArea>
          </div>
        </div>

        {/* RIGHT SIDEBAR — Signal + Risk */}
        <div className="w-60 shrink-0 border-l border-[#1c2333] bg-[#161b22] hidden lg:flex flex-col">
          <div className="flex border-b border-[#1c2333]">
            {[
              { id: 'signal', label: 'Sinal' },
              { id: 'risk', label: 'Risco' },
            ].map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={cn('flex-1 py-1.5 text-[11px] font-medium border-b-2 transition-colors',
                  activeTab === tab.id
                    ? 'border-blue-500 text-white'
                    : 'border-transparent text-[#6e7681] hover:text-white'
                )}>
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-hidden">
            {activeTab === 'signal' && (
              <div className="flex flex-col gap-2 overflow-y-auto h-full">
                <div className="p-2">
                  <FusionSignalCard symbol={symbol} timeframe={timeframe} compact />
                </div>
                <SignalPanel signals={signals} currentCandle={lastCandle} />
              </div>
            )}
            {activeTab === 'risk' && <RiskConfig config={riskConfig} onChange={setRiskConfig} />}
          </div>

          {/* Account mini-panel */}
          {connection && (
            <div className="border-t border-[#1c2333] p-3 grid grid-cols-2 gap-1.5 text-[10px] font-mono">
              <div>
                <p className="text-[#6e7681]">Saldo</p>
                <p className="text-white font-semibold">${(connection.balance || 0).toFixed(2)}</p>
              </div>
              <div>
                <p className="text-[#6e7681]">Patrimônio</p>
                <p className="text-[#26a69a] font-semibold">${(connection.equity || 0).toFixed(2)}</p>
              </div>
              <div>
                <p className="text-[#6e7681]">Margem</p>
                <p className="text-yellow-400 font-semibold">${(connection.margin || 0).toFixed(2)}</p>
              </div>
              <div>
                <p className="text-[#6e7681]">Livre</p>
                <p className="text-blue-400 font-semibold">${(connection.free_margin || 0).toFixed(2)}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
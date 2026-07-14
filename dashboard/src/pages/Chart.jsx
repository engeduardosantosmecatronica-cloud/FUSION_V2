import React, { useEffect, useMemo, useRef, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { XAxis, YAxis, Tooltip, ResponsiveContainer, Line, ComposedChart, ReferenceLine, Brush } from "recharts";

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];

function normalizeCandle(candle) {
  return {
    time: candle?.time || candle?.timestamp || Date.now(),
    open: Number(candle?.open ?? 0),
    high: Number(candle?.high ?? candle?.open ?? 0),
    low: Number(candle?.low ?? candle?.open ?? 0),
    close: Number(candle?.close ?? candle?.open ?? 0),
    volume: Number(candle?.volume ?? 0),
  };
}

function buildCandles(historyCandles, livePayload) {
  const candles = Array.isArray(historyCandles) ? historyCandles.map(normalizeCandle) : [];
  if (!candles.length) return candles;

  const liveCandle = livePayload?.current_candle;
  const latestTick = livePayload?.tick;
  const livePrice = Number(latestTick?.last ?? latestTick?.bid ?? latestTick?.ask ?? 0);

  if (liveCandle) {
    const current = normalizeCandle(liveCandle);
    const last = candles[candles.length - 1];
    const lastTime = Number(last?.time || 0);
    const currentTime = Number(current.time || 0);

    if (currentTime && currentTime > lastTime) {
      candles.push(current);
      return candles;
    }
  }

  if (livePrice > 0) {
    const last = candles[candles.length - 1];
    const updatedLast = {
      ...last,
      close: livePrice,
      high: Math.max(Number(last.high || 0), livePrice),
      low: Math.min(Number(last.low || 0), livePrice),
    };
    candles[candles.length - 1] = updatedLast;
  }

  return candles;
}

function calculateIndicators(candles) {
  const closes = candles.map((c) => Number(c.close || 0));

  const ma20 = closes.map((_, index) => {
    if (index < 19) return null;
    const slice = closes.slice(index - 19, index + 1);
    return Number((slice.reduce((sum, value) => sum + value, 0) / slice.length).toFixed(5));
  });

  const ma50 = closes.map((_, index) => {
    if (index < 49) return null;
    const slice = closes.slice(index - 49, index + 1);
    return Number((slice.reduce((sum, value) => sum + value, 0) / slice.length).toFixed(5));
  });

  const rsi = closes.map((close, index) => {
    if (index === 0) return 50;
    const changes = closes.slice(1, index + 1).map((value, offset) => value - closes[offset]);
    const gains = changes.filter((change) => change > 0).reduce((sum, change) => sum + change, 0);
    const losses = Math.abs(changes.filter((change) => change < 0).reduce((sum, change) => sum + change, 0));
    const avgGain = gains / Math.max(1, changes.length);
    const avgLoss = losses / Math.max(1, changes.length);
    if (avgLoss === 0) return 100;
    const rs = avgGain / avgLoss;
    return Number((100 - 100 / (1 + rs)).toFixed(2));
  });

  return { ma20, ma50, rsi };
}

function CandleOverlay({ width, height, data }) {
  if (!data?.length) return null;

  const safeWidth = Math.max(1, Number(width) || 640);
  const safeHeight = Math.max(1, Number(height) || 430);
  const padding = 12;
  const brushHeight = 45;
  const chartAreaLeft = padding + 60;
  const chartAreaRight = safeWidth - padding;
  const chartAreaTop = padding + 10;
  const chartAreaBottom = safeHeight - padding - brushHeight;
  const chartWidth = Math.max(1, chartAreaRight - chartAreaLeft);
  const chartHeight = Math.max(1, chartAreaBottom - chartAreaTop);
  const values = data.flatMap((entry) => [Number(entry.high ?? 0), Number(entry.low ?? 0), Number(entry.open ?? 0), Number(entry.close ?? 0)]);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const candleSpacing = chartWidth / Math.max(1, data.length);
  const bodyWidth = Math.max(4, Math.min(12, candleSpacing * 0.65));
  const range = maxValue - minValue || 1;

  const toY = (value) => {
    const ratio = (maxValue - Number(value)) / range;
    return chartAreaTop + Math.min(chartHeight, Math.max(0, ratio * chartHeight));
  };

  return (
    <svg width={safeWidth} height={safeHeight} viewBox={`0 0 ${safeWidth} ${safeHeight}`} className="absolute inset-0 pointer-events-none z-10" style={{ overflow: "hidden" }}>
      <defs>
        <clipPath id="candleClip">
          <rect x={chartAreaLeft} y={chartAreaTop} width={Math.max(1, chartWidth)} height={Math.max(1, chartHeight)} />
        </clipPath>
      </defs>
      <g clipPath="url(#candleClip)">
        {data.map((entry, index) => {
          const x = chartAreaLeft + (index + 0.5) * candleSpacing;
          const high = Number(entry.high ?? 0);
          const low = Number(entry.low ?? 0);
          const open = Number(entry.open ?? 0);
          const close = Number(entry.close ?? 0);
          const yHigh = toY(high);
          const yLow = toY(low);
          const yOpen = toY(open);
          const yClose = toY(close);
          const bodyTop = Math.min(yOpen, yClose);
          const bodyBottom = Math.max(yOpen, yClose);
          const bodyHeight = Math.max(1, bodyBottom - bodyTop);
          const isBullish = close >= open;
          const color = isBullish ? "#00d084" : "#ff4444";
          const wickStroke = isBullish ? "#00a366" : "#cc0000";
          const rectX = x - bodyWidth / 2;
          const clampedRectX = Math.max(chartAreaLeft, Math.min(chartAreaRight - bodyWidth, rectX));

          return (
            <g key={`${entry.time}-${index}`}>
              <line x1={x} x2={x} y1={yHigh} y2={yLow} stroke={wickStroke} strokeWidth={1.6} opacity={0.85} />
              <rect x={clampedRectX} y={bodyTop} width={bodyWidth} height={Math.max(1, bodyHeight)} rx={1.5} fill={color} stroke={isBullish ? "#1aff9f" : "#ff6666"} strokeWidth={0.7} />
            </g>
          );
        })}
      </g>
    </svg>
  );
}

export default function Chart() {
  const [symbol, setSymbol] = useState("AUDUSD");
  const [timeframe, setTimeframe] = useState("M15");
  const [candles, setCandles] = useState(/** @type {Array<any>} */ ([]));
  const [tick, setTick] = useState(/** @type {any} */ (null));
  const [source, setSource] = useState("");
  const [status, setStatus] = useState("connecting");
  const [error, setError] = useState("");
  const [visibleStart, setVisibleStart] = useState(0);
  const [visibleCount, setVisibleCount] = useState(80);
  const [dragging, setDragging] = useState(false);
  const [dragOriginX, setDragOriginX] = useState(0);
  const [dragOriginStart, setDragOriginStart] = useState(0);
  const chartContainerRef = useRef(null);
  const [chartSize, setChartSize] = useState({ width: 640, height: 430 });

  useEffect(() => {
    let cancelled = false;
    const load = async (initial = false) => {
      try {
        if (initial) await fusionApi.selectStream(symbol, timeframe, 300).catch(() => null);
        const [history, live] = await Promise.all([fusionApi.candles(symbol, timeframe, 300), fusionApi.live(symbol, timeframe)]);
        if (cancelled) return;
        const nextCandles = buildCandles(Array.isArray(history.candles) ? history.candles : [], live);
        setCandles(nextCandles);
        setTick(live.tick || null);
        setSource(history.source || live.source || "Fusion API");
        setStatus("online");
        setError("");
      } catch (err) {
        if (!cancelled) {
          setStatus("offline");
          setError(err instanceof Error ? err.message : "Falha ao acessar o Fusion");
        }
      }
    };
    load(true);
    const timer = window.setInterval(() => load(false), 1000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [symbol, timeframe]);

  useEffect(() => {
    const node = chartContainerRef.current;
    if (!node) return;
    const resize = () => {
      const nextWidth = node.clientWidth || 640;
      const nextHeight = node.clientHeight || 430;
      setChartSize({ width: nextWidth, height: nextHeight });
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(node);
    window.addEventListener("resize", resize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, []);

  const indicators = useMemo(() => calculateIndicators(candles), [candles]);
  const chartData = useMemo(() => candles.map((c, i) => ({
    time: new Date(c.time).toLocaleString("pt-BR", { day: "2-digit", hour: "2-digit", minute: "2-digit" }),
    open: Number(c.open), high: Number(c.high), low: Number(c.low), close: Number(c.close), volume: Number(c.volume || 0),
    body: [Number(c.open), Number(c.close)], wick: [Number(c.low), Number(c.high)], bullish: Number(c.close) >= Number(c.open),
    ma20: indicators.ma20[i], ma50: indicators.ma50[i], rsi: indicators.rsi[i],
  })), [candles, indicators]);

  useEffect(() => {
    setVisibleStart(0);
    setVisibleCount(Math.min(80, Math.max(20, chartData.length || 80)));
  }, [symbol, timeframe, chartData.length]);

  const visibleData = useMemo(() => {
    if (!chartData.length) return [];
    const start = Math.max(0, Math.min(visibleStart, chartData.length - 1));
    const end = Math.max(start + 1, Math.min(chartData.length, start + visibleCount));
    return chartData.slice(start, end);
  }, [chartData, visibleStart, visibleCount]);

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const handleWheel = (event) => {
    event.preventDefault();
    if (!chartData.length) return;
    if (event.deltaY > 0) {
      setVisibleCount((value) => Math.min(chartData.length, value + 5));
    } else {
      setVisibleCount((value) => Math.max(20, value - 5));
    }
  };
  const handleMouseDown = (event) => {
    setDragging(true);
    setDragOriginX(event.clientX);
    setDragOriginStart(visibleStart);
  };
  const handleMouseMove = (event) => {
    if (!dragging || !chartData.length) return;
    const delta = event.clientX - dragOriginX;
    const steps = Math.round(delta / 75);
    const nextStart = clamp(dragOriginStart - steps, 0, Math.max(0, chartData.length - visibleCount));
    setVisibleStart(nextStart);
  };
  const handleMouseUp = () => {
    setDragging(false);
  };
  const zoomIn = () => {
    setVisibleCount((value) => Math.max(20, Math.min(chartData.length, value - 10)));
  };
  const zoomOut = () => {
    setVisibleCount((value) => Math.min(chartData.length, value + 10));
  };
  const resetView = () => {
    setVisibleStart(0);
    setVisibleCount(Math.min(80, Math.max(20, chartData.length || 80)));
  };
  const handleBrushChange = (range) => {
    if (!range || range.startIndex == null || range.endIndex == null) return;
    const start = Math.max(0, range.startIndex);
    const end = Math.max(start + 1, range.endIndex + 1);
    setVisibleStart(start);
    setVisibleCount(Math.max(20, end - start));
  };

  const lastPrice = Number(tick?.last ?? tick?.bid ?? tick?.ask ?? candles.at(-1)?.close ?? 0);

  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h1 className="text-2xl font-bold tracking-tight">Gráfico Operacional</h1><p className="text-sm text-gray-500 mt-1">{symbol} • {timeframe} • {source || "conectando ao Fusion"}</p></div>
      <div className="flex flex-wrap items-center gap-2">
        <select value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} className="w-28 bg-[#1a2035] border border-[#2a3555] rounded px-3 py-1.5 text-sm text-white">
          {['AUDUSD', 'EURUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'WINQ25'].map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
        <div className="flex gap-1">
          <button onClick={zoomOut} className="px-2 py-1 rounded text-xs font-semibold bg-[#1a2035] text-gray-300 hover:bg-[#2a3555]">-</button>
          <button onClick={zoomIn} className="px-2 py-1 rounded text-xs font-semibold bg-[#1a2035] text-gray-300 hover:bg-[#2a3555]">+</button>
          <button onClick={resetView} className="px-2 py-1 rounded text-xs font-semibold bg-[#1a2035] text-gray-300 hover:bg-[#2a3555]">Reset</button>
        </div>
        <span className={status === "online" ? "px-2 py-1 rounded text-xs font-semibold bg-emerald-500/15 text-emerald-400" : "px-2 py-1 rounded text-xs font-semibold bg-red-500/15 text-red-400"}>{status === "online" ? "MT5 AO VIVO" : "DESCONECTADO"}</span>
      </div>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="text-sm text-gray-400">Último: <span className="text-white font-mono">{Number(lastPrice).toFixed(5)}</span>{tick && <span className="ml-4">Bid {tick.bid} • Ask {tick.ask} • Spread {tick.spread}</span>}</div>
      <div className="flex gap-1">{TIMEFRAMES.map(tf => <button key={tf} onClick={() => setTimeframe(tf)} className={timeframe === tf ? "px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500 text-white" : "px-2.5 py-1 rounded text-xs font-semibold bg-[#1a2035] text-gray-400"}>{tf}</button>)}</div>
    </div>
    <p className="text-xs text-gray-500">Roda do mouse para zoom • arraste para navegar • duplo clique para resetar</p>
    {error && <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-lg px-4 py-3 text-sm">API local indisponível: {error}. Inicie o serviço MT5 na porta 5000.</div>}
    <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4">
      {chartData.length ? <div ref={chartContainerRef} onWheel={handleWheel} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} onDoubleClick={resetView} style={{ cursor: dragging ? "grabbing" : "grab", touchAction: "none", position: "relative", height: 430, overflow: "hidden" }}>
        <ResponsiveContainer width="100%" height="100%"><ComposedChart data={visibleData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <XAxis dataKey="time" tick={{ fill: "#6b7280", fontSize: 10 }} minTickGap={45} /><YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7280", fontSize: 10 }} width={72} />
          <Tooltip contentStyle={{ background: "#1a2035", border: "1px solid #2a3555", borderRadius: 8, color: "#fff", fontSize: 12 }} />
          {lastPrice > 0 && <ReferenceLine y={lastPrice} stroke="#22d3ee" strokeDasharray="4 4" />}
          <Line type="monotone" dataKey="ma20" stroke="#3b82f6" dot={false} strokeWidth={1.5} /><Line type="monotone" dataKey="ma50" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
          <Brush dataKey="time" height={20} travellerWidth={8} startIndex={Math.max(0, visibleStart)} endIndex={Math.max(0, Math.min(chartData.length - 1, visibleStart + visibleData.length - 1))} onChange={handleBrushChange} stroke="#10b981" />
        </ComposedChart></ResponsiveContainer>
        <CandleOverlay width={chartSize.width} height={chartSize.height} data={visibleData} />
      </div> : <div className="h-[430px] flex items-center justify-center text-gray-500">Aguardando candles do MT5...</div>}
    </div>
    <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4"><h3 className="text-xs text-gray-500 uppercase tracking-wider mb-2">RSI (14)</h3>
      <ResponsiveContainer width="100%" height={120}><ComposedChart data={visibleData}><XAxis dataKey="time" hide /><YAxis domain={[0, 100]} width={30} ticks={[30, 50, 70]} /><ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" /><ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" /><Line type="monotone" dataKey="rsi" stroke="#a855f7" dot={false} strokeWidth={1.5} /></ComposedChart></ResponsiveContainer>
    </div>
  </div>;
}
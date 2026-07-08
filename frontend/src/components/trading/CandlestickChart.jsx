import React, { useRef, useEffect, useState, useCallback } from 'react';

const CANDLE_WIDTH_RATIO = 0.7;
const MIN_CANDLES_VIEW = 20;
const MAX_CANDLES_VIEW = 200;

export default function CandlestickChart({ candles, symbol, timeframe }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [viewRange, setViewRange] = useState({ start: 0, end: 0 });
  const [hoveredCandle, setHoveredCandle] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const isDragging = useRef(false);
  const lastDragX = useRef(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (candles.length > 0) {
      const visible = Math.min(60, candles.length);
      setViewRange({ start: Math.max(0, candles.length - visible), end: candles.length });
    }
  }, [candles.length]);

  const drawChart = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !dimensions.width || !dimensions.height) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    const w = dimensions.width;
    const h = dimensions.height;
    const padding = { top: 20, right: 70, bottom: 40, left: 12 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    // Background
    ctx.fillStyle = 'hsl(220, 18%, 9%)';
    ctx.fillRect(0, 0, w, h);

    const visibleCandles = candles.slice(viewRange.start, viewRange.end);
    if (visibleCandles.length === 0) {
      ctx.fillStyle = 'hsl(215, 14%, 40%)';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Aguardando dados de candles...', w / 2, h / 2);
      return;
    }

    const allHigh = Math.max(...visibleCandles.map(c => c.high));
    const allLow = Math.min(...visibleCandles.map(c => c.low));
    const priceRange = allHigh - allLow || 1;
    const priceMargin = priceRange * 0.08;
    const minPrice = allLow - priceMargin;
    const maxPrice = allHigh + priceMargin;
    const totalRange = maxPrice - minPrice;

    const toY = (price) => padding.top + chartH - ((price - minPrice) / totalRange) * chartH;
    const candleSpacing = chartW / visibleCandles.length;
    const candleWidth = Math.max(2, candleSpacing * CANDLE_WIDTH_RATIO);

    // Grid lines
    const gridLines = 6;
    ctx.strokeStyle = 'hsl(220, 14%, 13%)';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([2, 4]);
    for (let i = 0; i <= gridLines; i++) {
      const price = minPrice + (totalRange / gridLines) * i;
      const y = toY(price);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();

      // Price label
      ctx.fillStyle = 'hsl(215, 14%, 40%)';
      ctx.font = '11px JetBrains Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(price.toFixed(5), w - padding.right + 8, y + 4);
    }
    ctx.setLineDash([]);

    // Draw candles
    visibleCandles.forEach((candle, i) => {
      const x = padding.left + i * candleSpacing + candleSpacing / 2;
      const isBullish = candle.close >= candle.open;
      const bullColor = '#22c55e';
      const bearColor = '#ef4444';
      const color = isBullish ? bullColor : bearColor;

      // Wick
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, toY(candle.high));
      ctx.lineTo(x, toY(candle.low));
      ctx.stroke();

      // Body
      const bodyTop = toY(Math.max(candle.open, candle.close));
      const bodyBottom = toY(Math.min(candle.open, candle.close));
      const bodyHeight = Math.max(1, bodyBottom - bodyTop);

      ctx.fillStyle = color;
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);

      // Volume bars at bottom
      const maxVol = Math.max(...visibleCandles.map(c => c.volume || 0)) || 1;
      const volH = ((candle.volume || 0) / maxVol) * (chartH * 0.12);
      ctx.fillStyle = isBullish ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)';
      ctx.fillRect(x - candleWidth / 2, padding.top + chartH - volH, candleWidth, volH);
    });

    // Time labels
    ctx.fillStyle = 'hsl(215, 14%, 40%)';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    const labelInterval = Math.max(1, Math.floor(visibleCandles.length / 8));
    visibleCandles.forEach((candle, i) => {
      if (i % labelInterval === 0) {
        const x = padding.left + i * candleSpacing + candleSpacing / 2;
        const date = new Date(candle.timestamp);
        const label = `${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')}`;
        ctx.fillText(label, x, h - padding.bottom + 18);
      }
    });

    // Crosshair
    if (hoveredCandle && mousePos.x > padding.left && mousePos.x < w - padding.right) {
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 0.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(mousePos.x, padding.top);
      ctx.lineTo(mousePos.x, padding.top + chartH);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(padding.left, mousePos.y);
      ctx.lineTo(w - padding.right, mousePos.y);
      ctx.stroke();
      ctx.setLineDash([]);

      // Price at cursor
      const cursorPrice = minPrice + ((padding.top + chartH - mousePos.y) / chartH) * totalRange;
      ctx.fillStyle = 'hsl(210, 100%, 52%)';
      ctx.fillRect(w - padding.right, mousePos.y - 10, padding.right, 20);
      ctx.fillStyle = '#fff';
      ctx.font = '11px JetBrains Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(cursorPrice.toFixed(5), w - padding.right + 6, mousePos.y + 4);
    }

    // Current price line
    if (visibleCandles.length > 0) {
      const lastCandle = visibleCandles[visibleCandles.length - 1];
      const lastY = toY(lastCandle.close);
      const lastColor = lastCandle.close >= lastCandle.open ? '#22c55e' : '#ef4444';
      ctx.strokeStyle = lastColor;
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(padding.left, lastY);
      ctx.lineTo(w - padding.right, lastY);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = lastColor;
      ctx.fillRect(w - padding.right, lastY - 10, padding.right, 20);
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px JetBrains Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(lastCandle.close.toFixed(5), w - padding.right + 6, lastY + 4);
    }
  }, [candles, viewRange, dimensions, hoveredCandle, mousePos]);

  useEffect(() => {
    drawChart();
  }, [drawChart]);

  const handleMouseMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setMousePos({ x, y });

    const padding = { left: 12, right: 70 };
    const chartW = dimensions.width - padding.left - padding.right;
    const visibleCandles = candles.slice(viewRange.start, viewRange.end);
    const candleSpacing = chartW / visibleCandles.length;
    const idx = Math.floor((x - padding.left) / candleSpacing);
    if (idx >= 0 && idx < visibleCandles.length) {
      setHoveredCandle(visibleCandles[idx]);
    } else {
      setHoveredCandle(null);
    }

    if (isDragging.current) {
      const dx = e.clientX - lastDragX.current;
      lastDragX.current = e.clientX;
      const candleShift = Math.round(dx / candleSpacing);
      if (candleShift !== 0) {
        setViewRange(prev => {
          const range = prev.end - prev.start;
          let newStart = prev.start - candleShift;
          newStart = Math.max(0, Math.min(candles.length - range, newStart));
          return { start: newStart, end: newStart + range };
        });
      }
    }
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const zoomDir = e.deltaY > 0 ? 1 : -1;
    setViewRange(prev => {
      const range = prev.end - prev.start;
      let newRange = range + zoomDir * 3;
      newRange = Math.max(MIN_CANDLES_VIEW, Math.min(MAX_CANDLES_VIEW, Math.min(candles.length, newRange)));
      const center = (prev.start + prev.end) / 2;
      let newStart = Math.round(center - newRange / 2);
      newStart = Math.max(0, Math.min(candles.length - newRange, newStart));
      return { start: newStart, end: newStart + newRange };
    });
  };

  const handleMouseDown = (e) => {
    isDragging.current = true;
    lastDragX.current = e.clientX;
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  return (
    <div className="relative w-full h-full" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-crosshair"
        style={{ width: dimensions.width, height: dimensions.height }}
        onMouseMove={handleMouseMove}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => { setHoveredCandle(null); isDragging.current = false; }}
      />
      {/* OHLCV Overlay */}
      {hoveredCandle && (
        <div className="absolute top-2 left-3 flex gap-4 text-xs font-mono">
          <span className="text-muted-foreground">O <span className="text-foreground">{hoveredCandle.open.toFixed(5)}</span></span>
          <span className="text-muted-foreground">H <span className="text-green-400">{hoveredCandle.high.toFixed(5)}</span></span>
          <span className="text-muted-foreground">L <span className="text-red-400">{hoveredCandle.low.toFixed(5)}</span></span>
          <span className="text-muted-foreground">C <span className={hoveredCandle.close >= hoveredCandle.open ? 'text-green-400' : 'text-red-400'}>{hoveredCandle.close.toFixed(5)}</span></span>
          <span className="text-muted-foreground">V <span className="text-foreground">{(hoveredCandle.volume || 0).toLocaleString()}</span></span>
        </div>
      )}
    </div>
  );
}
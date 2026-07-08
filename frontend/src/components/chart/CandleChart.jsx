import React, { useRef, useEffect, useState, useCallback } from 'react';
import { renderChart } from './CandleRenderer';
import { ChartBuffer } from './ChartBuffer';

export default function CandleChart({ candles, indicators, currentTick }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const bufferRef = useRef(new ChartBuffer(500));
  const metaRef = useRef(null); // renderChart returns metadata
  const [crosshair, setCrosshair] = useState(null);
  const [hoveredCandle, setHoveredCandle] = useState(null);
  const [dims, setDims] = useState({ w: 0, h: 0 });
  const isDragging = useRef(false);
  const lastDragX = useRef(0);
  const rafRef = useRef(null);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Load candles into buffer when array changes
  useEffect(() => {
    bufferRef.current.load(candles);
    scheduleDraw();
  }, [candles]);

  const scheduleDraw = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const visible = bufferRef.current.getVisible();
      if (visible.length === 0) {
        // Draw empty state
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        canvas.width = canvas.clientWidth * dpr;
        canvas.height = canvas.clientHeight * dpr;
        ctx.scale(dpr, dpr);
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
        ctx.fillStyle = '#6e7681';
        ctx.font = '14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Aguardando dados — clique em "Gerar Demo" para começar', canvas.clientWidth / 2, canvas.clientHeight / 2);
        return;
      }
      metaRef.current = renderChart(canvas, visible, indicators, crosshair);
    });
  }, [indicators, crosshair]);

  useEffect(() => { scheduleDraw(); }, [scheduleDraw, dims]);

  // Mouse events
  const handleMouseMove = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setCrosshair({ x, y });

    // Find hovered candle
    const meta = metaRef.current;
    if (meta) {
      const idx = Math.floor((x - meta.PAD.left) / meta.slotW);
      const visible = bufferRef.current.getVisible();
      if (idx >= 0 && idx < visible.length) {
        setHoveredCandle(visible[idx]);
      } else {
        setHoveredCandle(null);
      }
    }

    if (isDragging.current && meta) {
      const dx = e.clientX - lastDragX.current;
      lastDragX.current = e.clientX;
      const shift = Math.round(-dx / meta.slotW);
      if (shift !== 0) {
        bufferRef.current.pan(shift);
        scheduleDraw();
      }
    }
  }, [scheduleDraw]);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 5 : -5;
    bufferRef.current.zoom(delta);
    scheduleDraw();
  }, [scheduleDraw]);

  const handleMouseDown = (e) => { isDragging.current = true; lastDragX.current = e.clientX; };
  const handleMouseUp = () => { isDragging.current = false; };
  const handleMouseLeave = () => { isDragging.current = false; setCrosshair(null); setHoveredCandle(null); };

  // Redraw when crosshair moves (only affects overlay layer — cheap)
  useEffect(() => { scheduleDraw(); }, [crosshair]);

  const dec = hoveredCandle?.close > 1000 ? 2 : hoveredCandle?.close > 100 ? 3 : 5;
  const isBull = hoveredCandle ? hoveredCandle.close >= hoveredCandle.open : true;

  return (
    <div ref={containerRef} className="relative w-full h-full bg-[#0d1117] overflow-hidden">
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-crosshair select-none"
        onMouseMove={handleMouseMove}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />

      {/* OHLCV tooltip */}
      {hoveredCandle && (
        <div className="absolute top-2 left-2 flex gap-3 text-[11px] font-mono bg-[#0d1117]/80 px-2 py-1 rounded pointer-events-none select-none">
          <span className="text-[#6e7681]">O <span className="text-white">{hoveredCandle.open.toFixed(dec)}</span></span>
          <span className="text-[#6e7681]">H <span className="text-[#26a69a]">{hoveredCandle.high.toFixed(dec)}</span></span>
          <span className="text-[#6e7681]">L <span className="text-[#ef5350]">{hoveredCandle.low.toFixed(dec)}</span></span>
          <span className="text-[#6e7681]">C <span className={isBull ? 'text-[#26a69a]' : 'text-[#ef5350]'}>{hoveredCandle.close.toFixed(dec)}</span></span>
          <span className="text-[#6e7681]">V <span className="text-white">{(hoveredCandle.volume || 0).toLocaleString()}</span></span>
        </div>
      )}

      {/* Live tick price overlay (top right) */}
      {currentTick && (
        <div className="absolute top-2 right-20 text-[11px] font-mono text-[#6e7681] pointer-events-none">
          Bid <span className="text-white">{currentTick.bid?.toFixed(dec)}</span>
          {' · '}
          Ask <span className="text-white">{currentTick.ask?.toFixed(dec)}</span>
          {' · '}
          Spread <span className="text-yellow-400">{currentTick.spread?.toFixed(1)}</span>
        </div>
      )}

      {/* Zoom hint */}
      <div className="absolute bottom-9 left-2 text-[10px] text-[#3d4553] pointer-events-none select-none">
        Scroll para zoom · Arrastar para pan
      </div>
    </div>
  );
}
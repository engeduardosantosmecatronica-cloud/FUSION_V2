// Renderer Canvas2D puro â€” sem bibliotecas externas
// Todas as funÃ§Ãµes sÃ£o puras e testÃ¡veis

const COLORS = {
  bg: '#0d1117',
  grid: '#1c2333',
  gridText: '#6e7681',
  bull: '#26a69a',
  bear: '#ef5350',
  bullBorder: '#1a7a70',
  bearBorder: '#b33b38',
  wick: null, // usa mesma cor do corpo
  crosshair: 'rgba(255,255,255,0.2)',
  priceLabel: '#1d6fa3',
  currentPrice: { bull: '#26a69a', bear: '#ef5350' },
  volume: { bull: 'rgba(38,166,154,0.18)', bear: 'rgba(239,83,80,0.18)' },
  overlay: {
    ema1: '#f59e0b',
    ema2: '#3b82f6',
    ema3: '#8b5cf6',
    bollUpper: '#06b6d4',
    bollMiddle: '#0284c7',
    bollLower: '#06b6d4',
    entry: '#e5e7eb',
    stop: '#ef4444',
    target: '#22c55e',
    support: '#38bdf8',
    resistance: '#f59e0b',
    blocked: '#94a3b8',
  },
  rsiLine: '#a78bfa',
  rsiOverbought: '#ef4444',
  rsiOversold: '#22c55e',
  macdLine: '#3b82f6',
  macdSignal: '#f97316',
  macdHistBull: '#26a69a',
  macdHistBear: '#ef5350',
};

const PAD = { top: 24, right: 72, bottom: 32, left: 0 };
const VOL_HEIGHT_RATIO = 0.12;
const RSI_HEIGHT = 80;
const MACD_HEIGHT = 70;


function collectOverlayPrices(overlays = {}) {
  const prices = [];
  const push = (item) => {
    const price = Number(item?.price);
    if (Number.isFinite(price) && price > 0) prices.push(price);
  };
  (overlays.entries || []).forEach(push);
  (overlays.sl_levels || []).forEach(push);
  (overlays.tp_levels || []).forEach(push);
  (overlays.support_resistance || []).forEach(push);
  (overlays.signals || []).forEach(push);
  return prices;
}

function drawFusionLevel(ctx, { y, price, label, color, dec, W, dashed = false }) {
  if (!Number.isFinite(y)) return;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.25;
  ctx.setLineDash(dashed ? [5, 5] : []);
  ctx.beginPath();
  ctx.moveTo(PAD.left, y);
  ctx.lineTo(W - PAD.right, y);
  ctx.stroke();
  ctx.setLineDash([]);

  const text = `${label} ${price.toFixed(dec)}`;
  ctx.font = 'bold 10px JetBrains Mono, monospace';
  const tw = ctx.measureText(text).width + 10;
  const x = Math.max(PAD.left + 4, W - PAD.right - tw - 4);
  ctx.fillStyle = 'rgba(13,17,23,0.86)';
  ctx.fillRect(x, y - 9, tw, 18);
  ctx.fillStyle = color;
  ctx.textAlign = 'left';
  ctx.fillText(text, x + 5, y + 4);
  ctx.restore();
}

function drawFusionOverlays(ctx, overlays = {}, toY, W, dec) {
  const drawItems = (items, label, color, dashed = false) => {
    (items || []).forEach((item) => {
      const price = Number(item?.price);
      if (!Number.isFinite(price) || price <= 0) return;
      const itemLabel = item?.direction ? `${label} ${item.direction}` : label;
      drawFusionLevel(ctx, { y: toY(price), price, label: itemLabel, color, dec, W, dashed });
    });
  };

  drawItems(overlays.support_resistance?.filter(x => x.type === 'support'), 'Suporte', COLORS.overlay.support, true);
  drawItems(overlays.support_resistance?.filter(x => x.type === 'resistance'), 'Resist.', COLORS.overlay.resistance, true);
  drawItems(overlays.sl_levels, 'SL', COLORS.overlay.stop);
  drawItems(overlays.tp_levels, 'TP', COLORS.overlay.target);
  drawItems(overlays.entries, 'Entrada', COLORS.overlay.entry);
  drawItems((overlays.signals || []).filter(x => x.blocked), 'Bloqueado', COLORS.overlay.blocked, true);
}
function getPriceDecimals(price) {
  if (!price) return 5;
  if (price > 1000) return 2;
  if (price > 100) return 3;
  return 5;
}

export function renderChart(canvas, candles, indicators = {}, crosshair = null, overlays = {}) {
  if (!canvas || candles.length === 0) return null;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth;
  const H = canvas.clientHeight;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  ctx.scale(dpr, dpr);

  const hasRSI = indicators.rsi?.values?.length > 0;
  const hasMACD = indicators.macd?.macd?.length > 0;
  const subH = (hasRSI ? RSI_HEIGHT : 0) + (hasMACD ? MACD_HEIGHT : 0);

  const chartH = H - PAD.top - PAD.bottom - subH;
  const chartW = W - PAD.left - PAD.right;

  const dec = getPriceDecimals(candles[0]?.close);

  // Background
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, W, H);

  // Price range
  const overlayPrices = collectOverlayPrices(overlays);
  const highs = candles.map(c => c.high).concat(overlayPrices);
  const lows = candles.map(c => c.low).concat(overlayPrices);
  const maxP = Math.max(...highs);
  const minP = Math.min(...lows);
  const priceRange = maxP - minP || 0.001;
  const margin = priceRange * 0.08;
  const pMin = minP - margin;
  const pMax = maxP + margin;
  const pRange = pMax - pMin;

  const toY = (price) => PAD.top + chartH - ((price - pMin) / pRange) * chartH;
  const n = candles.length;
  const slotW = chartW / n;
  const candleW = Math.max(1, slotW * 0.7);
  const toX = (i) => PAD.left + i * slotW + slotW / 2;

  // Volume range
  const maxVol = Math.max(...candles.map(c => c.volume || 0)) || 1;
  const volBaseY = PAD.top + chartH;
  const volMaxH = chartH * VOL_HEIGHT_RATIO;

  // Grid
  const gridCount = 6;
  ctx.setLineDash([]);
  for (let i = 0; i <= gridCount; i++) {
    const p = pMin + (pRange / gridCount) * i;
    const y = toY(p);
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(W - PAD.right, y);
    ctx.stroke();
    ctx.fillStyle = COLORS.gridText;
    ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(p.toFixed(dec), W - PAD.right + 6, y + 4);
  }

  // Volume bars (behind candles)
  candles.forEach((c, i) => {
    const vol = c.volume || 0;
    const vH = (vol / maxVol) * volMaxH;
    const isBull = c.close >= c.open;
    ctx.fillStyle = isBull ? COLORS.volume.bull : COLORS.volume.bear;
    ctx.fillRect(toX(i) - candleW / 2, volBaseY - vH, candleW, vH);
  });

  // Bollinger bands
  if (indicators.boll) {
    const { upper, middle, lower } = indicators.boll;
    const drawBollLine = (vals, color, dash = []) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.setLineDash(dash);
      ctx.beginPath();
      let started = false;
      vals.forEach((v, i) => {
        if (v === null) return;
        const x = toX(i); const y = toY(v);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    };
    // Fill between bands
    ctx.beginPath();
    let started = false;
    upper.forEach((v, i) => {
      if (v === null) return;
      if (!started) { ctx.moveTo(toX(i), toY(v)); started = true; }
      else ctx.lineTo(toX(i), toY(v));
    });
    for (let i = lower.length - 1; i >= 0; i--) {
      if (lower[i] !== null) ctx.lineTo(toX(i), toY(lower[i]));
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(6,182,212,0.04)';
    ctx.fill();
    drawBollLine(upper, 'rgba(6,182,212,0.5)', [3, 3]);
    drawBollLine(middle, 'rgba(2,132,199,0.4)', [2, 4]);
    drawBollLine(lower, 'rgba(6,182,212,0.5)', [3, 3]);
  }

  // EMA lines
  const drawLine = (vals, color, width = 1.5) => {
    if (!vals) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.setLineDash([]);
    ctx.beginPath();
    let started = false;
    vals.forEach((v, i) => {
      if (v === null) return;
      const x = toX(i); const y = toY(v);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };
  if (indicators.ema1) drawLine(indicators.ema1.values, indicators.ema1.color || COLORS.overlay.ema1);
  if (indicators.ema2) drawLine(indicators.ema2.values, indicators.ema2.color || COLORS.overlay.ema2);
  if (indicators.ema3) drawLine(indicators.ema3.values, indicators.ema3.color || COLORS.overlay.ema3);

  // Candles
  candles.forEach((c, i) => {
    const isBull = c.close >= c.open;
    const color = isBull ? COLORS.bull : COLORS.bear;
    const x = toX(i);
    const highY = toY(c.high);
    const lowY = toY(c.low);
    const openY = toY(c.open);
    const closeY = toY(c.close);
    const bodyTop = Math.min(openY, closeY);
    const bodyH = Math.max(1, Math.abs(closeY - openY));

    // Wick
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();

    // Body
    ctx.fillStyle = color;
    if (candleW > 3) {
      ctx.fillRect(x - candleW / 2, bodyTop, candleW, bodyH);
      // Border
      ctx.strokeStyle = isBull ? COLORS.bullBorder : COLORS.bearBorder;
      ctx.lineWidth = 0.5;
      ctx.strokeRect(x - candleW / 2, bodyTop, candleW, bodyH);
    } else {
      ctx.fillRect(x - 0.5, bodyTop, 1, bodyH);
    }
  });

  // Fusion levels from MT5/Fusion signal panel
  drawFusionOverlays(ctx, overlays, toY, W, dec);

  // Current price dashed line
  const last = candles[candles.length - 1];
  if (last) {
    const isBull = last.close >= last.open;
    const lineColor = isBull ? COLORS.currentPrice.bull : COLORS.currentPrice.bear;
    const lastY = toY(last.close);
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(PAD.left, lastY);
    ctx.lineTo(W - PAD.right, lastY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = lineColor;
    ctx.fillRect(W - PAD.right, lastY - 10, PAD.right, 20);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 11px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(last.close.toFixed(dec), W - PAD.right + 5, lastY + 4);
  }

  // Time axis
  ctx.fillStyle = COLORS.gridText;
  ctx.font = '10px JetBrains Mono, monospace';
  ctx.textAlign = 'center';
  const labelEvery = Math.max(1, Math.floor(n / 8));
  candles.forEach((c, i) => {
    if (i % labelEvery !== 0) return;
    const d = new Date(c.timestamp);
    const label = `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
    ctx.fillText(label, toX(i), PAD.top + chartH + 18);
  });

  // Crosshair
  if (crosshair && crosshair.x > PAD.left && crosshair.x < W - PAD.right) {
    ctx.strokeStyle = COLORS.crosshair;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(crosshair.x, PAD.top);
    ctx.lineTo(crosshair.x, PAD.top + chartH);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(PAD.left, crosshair.y);
    ctx.lineTo(W - PAD.right, crosshair.y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Price label at crosshair
    const crossPrice = pMin + ((PAD.top + chartH - crosshair.y) / chartH) * pRange;
    ctx.fillStyle = '#1d6fa3';
    ctx.fillRect(W - PAD.right, crosshair.y - 10, PAD.right, 20);
    ctx.fillStyle = '#fff';
    ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(crossPrice.toFixed(dec), W - PAD.right + 5, crosshair.y + 4);
  }

  // RSI sub-panel
  let subY = PAD.top + chartH + PAD.bottom;
  if (hasRSI) {
    const vals = indicators.rsi.values;
    const rsiY = (v) => subY + RSI_HEIGHT - (v / 100) * RSI_HEIGHT;

    ctx.fillStyle = '#111827';
    ctx.fillRect(0, subY, W - PAD.right, RSI_HEIGHT);

    // Overbought / Oversold lines
    [30, 50, 70].forEach(level => {
      const y = rsiY(level);
      ctx.strokeStyle = level === 50 ? COLORS.grid : (level === 70 ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)');
      ctx.lineWidth = 0.5;
      ctx.setLineDash(level === 50 ? [2, 4] : []);
      ctx.beginPath();
      ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = COLORS.gridText;
      ctx.font = '9px JetBrains Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(level, W - PAD.right + 4, y + 3);
    });

    ctx.strokeStyle = COLORS.rsiLine;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([]);
    ctx.beginPath();
    let started = false;
    vals.forEach((v, i) => {
      if (v === null || i >= n) return;
      const x = toX(i); const y = rsiY(v);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.fillStyle = COLORS.gridText;
    ctx.font = '9px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.fillText('RSI', 4, subY + 10);

    if (crosshair && vals[Math.round((crosshair.x - PAD.left) / slotW)] !== null) {
      const idx = Math.min(n - 1, Math.max(0, Math.floor((crosshair.x - PAD.left) / slotW)));
      const rsiVal = vals[idx];
      if (rsiVal !== null) {
        ctx.fillStyle = COLORS.rsiLine;
        ctx.fillText(rsiVal.toFixed(1), 28, subY + 10);
      }
    }

    subY += RSI_HEIGHT;
  }

  // MACD sub-panel
  if (hasMACD) {
    const { macd, signal, histogram } = indicators.macd;
    const macdVals = [...macd, ...signal].filter(v => v !== null);
    const histVals = histogram.filter(v => v !== null);
    const allMacd = [...macdVals, ...histVals];
    const macdMax = Math.max(...allMacd.map(Math.abs)) || 0.001;
    const macdY = (v) => subY + MACD_HEIGHT / 2 - (v / macdMax) * (MACD_HEIGHT / 2 - 4);

    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, subY, W - PAD.right, MACD_HEIGHT);

    // Zero line
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(PAD.left, subY + MACD_HEIGHT / 2);
    ctx.lineTo(W - PAD.right, subY + MACD_HEIGHT / 2);
    ctx.stroke();

    // Histogram
    histogram.forEach((v, i) => {
      if (v === null || i >= n) return;
      const x = toX(i);
      const y0 = subY + MACD_HEIGHT / 2;
      const yv = macdY(v);
      ctx.fillStyle = v >= 0 ? COLORS.macdHistBull : COLORS.macdHistBear;
      ctx.globalAlpha = 0.7;
      ctx.fillRect(x - candleW / 2, Math.min(y0, yv), candleW, Math.abs(y0 - yv));
      ctx.globalAlpha = 1;
    });

    const drawMacdLine = (vals, color) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      let s = false;
      vals.forEach((v, i) => {
        if (v === null || i >= n) return;
        const x = toX(i); const y = macdY(v);
        if (!s) { ctx.moveTo(x, y); s = true; } else ctx.lineTo(x, y);
      });
      ctx.stroke();
    };
    drawMacdLine(macd, COLORS.macdLine);
    drawMacdLine(signal, COLORS.macdSignal);

    ctx.fillStyle = COLORS.gridText;
    ctx.font = '9px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.fillText('MACD', 4, subY + 10);
  }

  // Return metadata for tooltip
  return { toX, toY, slotW, PAD, chartH, dec, pMin, pRange };
}




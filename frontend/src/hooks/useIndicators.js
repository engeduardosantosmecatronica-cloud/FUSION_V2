import { useEffect, useRef, useState, useCallback } from 'react';

// Cálculos inline (sem Web Worker para compatibilidade máxima)
// Em produção, mover para worker.js

function calcEMA(closes, period) {
  if (closes.length < period) return [];
  const k = 2 / (period + 1);
  const result = new Array(closes.length).fill(null);
  let ema = closes.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result[period - 1] = ema;
  for (let i = period; i < closes.length; i++) {
    ema = closes[i] * k + ema * (1 - k);
    result[i] = ema;
  }
  return result;
}

function calcSMA(closes, period) {
  const result = new Array(closes.length).fill(null);
  for (let i = period - 1; i < closes.length; i++) {
    const sum = closes.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
    result[i] = sum / period;
  }
  return result;
}

function calcRSI(closes, period = 14) {
  if (closes.length < period + 1) return [];
  const result = new Array(closes.length).fill(null);
  let gains = 0, losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  for (let i = period; i < closes.length; i++) {
    if (i > period) {
      const diff = closes[i] - closes[i - 1];
      avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
      avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period;
    }
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result[i] = 100 - 100 / (1 + rs);
  }
  return result;
}

function calcBollinger(closes, period = 20, stdMult = 2) {
  const sma = calcSMA(closes, period);
  const upper = new Array(closes.length).fill(null);
  const lower = new Array(closes.length).fill(null);

  for (let i = period - 1; i < closes.length; i++) {
    const slice = closes.slice(i - period + 1, i + 1);
    const mean = sma[i];
    const std = Math.sqrt(slice.reduce((acc, v) => acc + (v - mean) ** 2, 0) / period);
    upper[i] = mean + stdMult * std;
    lower[i] = mean - stdMult * std;
  }
  return { middle: sma, upper, lower };
}

function calcMACD(closes, fast = 12, slow = 26, signal = 9) {
  const emaFast = calcEMA(closes, fast);
  const emaSlow = calcEMA(closes, slow);
  const macdLine = closes.map((_, i) =>
    emaFast[i] !== null && emaSlow[i] !== null ? emaFast[i] - emaSlow[i] : null
  );
  const validMacd = macdLine.filter(v => v !== null);
  const signalRaw = calcEMA(validMacd, signal);

  const signalLine = new Array(closes.length).fill(null);
  let sigIdx = 0;
  for (let i = 0; i < closes.length; i++) {
    if (macdLine[i] !== null) {
      signalLine[i] = signalRaw[sigIdx++] ?? null;
    }
  }

  const histogram = closes.map((_, i) =>
    macdLine[i] !== null && signalLine[i] !== null ? macdLine[i] - signalLine[i] : null
  );

  return { macd: macdLine, signal: signalLine, histogram };
}

export function useIndicators(candles, config = {}) {
  const {
    ema1Period = 9,
    ema2Period = 21,
    ema3Period = 50,
    rsiPeriod = 14,
    bollPeriod = 20,
    showEMA1 = true,
    showEMA2 = true,
    showEMA3 = false,
    showBoll = false,
    showRSI = true,
    showMACD = false,
  } = config;

  const [indicators, setIndicators] = useState({});
  const lastLengthRef = useRef(0);

  const calculate = useCallback(() => {
    if (!candles || candles.length < 2) return;
    // Otimização: só recalcula se array cresceu ou mudou muito
    const closes = candles.map(c => c.close);

    const result = {};
    if (showEMA1) result.ema1 = { values: calcEMA(closes, ema1Period), period: ema1Period, color: '#f59e0b' };
    if (showEMA2) result.ema2 = { values: calcEMA(closes, ema2Period), period: ema2Period, color: '#3b82f6' };
    if (showEMA3) result.ema3 = { values: calcEMA(closes, ema3Period), period: ema3Period, color: '#8b5cf6' };
    if (showBoll) result.boll = { ...calcBollinger(closes, bollPeriod), color: '#06b6d4' };
    if (showRSI) result.rsi = { values: calcRSI(closes, rsiPeriod), period: rsiPeriod };
    if (showMACD) result.macd = calcMACD(closes);

    setIndicators(result);
    lastLengthRef.current = candles.length;
  }, [candles, ema1Period, ema2Period, ema3Period, rsiPeriod, bollPeriod, showEMA1, showEMA2, showEMA3, showBoll, showRSI, showMACD]);

  useEffect(() => {
    const id = requestAnimationFrame(calculate);
    return () => cancelAnimationFrame(id);
  }, [calculate]);

  return indicators;
}
const MT5_API_BASE_URL = import.meta.env.VITE_MT5_API_BASE_URL || 'http://localhost:5000';

async function requestJson(path, options = {}) {
  const response = await fetch(new URL(path, MT5_API_BASE_URL), {
    headers: { Accept: 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`MT5 request failed (${response.status}): ${text || response.statusText}`);
  }
  return response.json();
}

export async function setMt5Stream(symbol, timeframe, limit = 500) {
  return requestJson('/api/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, timeframe, limit }),
  });
}

export async function fetchMt5LiveState(symbol, timeframe) {
  return requestJson(`/api/live?symbol=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(timeframe)}`);
}

export async function fetchMt5Candles(symbol, timeframe, limit = 200) {
  const data = await requestJson(`/api/candles?symbol=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(timeframe)}&limit=${encodeURIComponent(String(limit))}`);
  const candles = Array.isArray(data) ? data : Array.isArray(data?.candles) ? data.candles : [];
  return candles.map((c) => ({
    symbol,
    timeframe,
    open: Number(c.open ?? c.Open ?? c.o ?? 0),
    high: Number(c.high ?? c.High ?? c.h ?? 0),
    low: Number(c.low ?? c.Low ?? c.l ?? 0),
    close: Number(c.close ?? c.Close ?? c.c ?? 0),
    volume: Number(c.volume ?? c.Volume ?? c.v ?? c.tick_volume ?? 0),
    timestamp: c.timestamp ?? c.time ?? c.Time ?? c.date ?? c.Date,
  })).filter((c) => c.timestamp && Number.isFinite(c.open) && Number.isFinite(c.high) && Number.isFinite(c.low) && Number.isFinite(c.close));
}

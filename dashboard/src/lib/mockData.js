// Simulated market data generator for the trading dashboard
export function generateCandles(count = 100) {
  const candles = [];
  let price = 128500;
  const now = Date.now();
  for (let i = count - 1; i >= 0; i--) {
    const open = price + (Math.random() - 0.5) * 200;
    const close = open + (Math.random() - 0.5) * 300;
    const high = Math.max(open, close) + Math.random() * 150;
    const low = Math.min(open, close) - Math.random() * 150;
    const volume = Math.floor(Math.random() * 5000) + 1000;
    candles.push({
      time: now - i * 5 * 60 * 1000,
      open: Math.round(open),
      high: Math.round(high),
      low: Math.round(low),
      close: Math.round(close),
      volume,
    });
    price = close;
  }
  return candles;
}

export function generateIndicators(candles) {
  const closes = candles.map(c => c.close);
  const ma20 = closes.map((_, i) => {
    if (i < 19) return null;
    const slice = closes.slice(i - 19, i + 1);
    return Math.round(slice.reduce((a, b) => a + b, 0) / 20);
  });
  const ma50 = closes.map((_, i) => {
    if (i < 49) return null;
    const slice = closes.slice(i - 49, i + 1);
    return Math.round(slice.reduce((a, b) => a + b, 0) / 50);
  });
  const rsi = closes.map(() => Math.round(30 + Math.random() * 40));
  const macd = closes.map(() => Math.round((Math.random() - 0.5) * 100));
  const signal = macd.map((v) => Math.round(v * 0.8));
  return { ma20, ma50, rsi, macd, signal };
}

export const mockAccountInfo = {
  broker: "XP Investimentos",
  server: "XPInc-MT5",
  account: "12345678",
  type: "Demo",
  balance: 100000,
  equity: 101250,
  margin_free: 98500,
  daily_pnl: 1250,
  daily_drawdown: -350,
  total_drawdown: -1200,
  leverage: "1:100",
  currency: "BRL",
};

export const mockSystemHealth = {
  mt5_connected: true,
  api_active: true,
  market_latency: 45,
  last_candle_age: 12,
  cpu_usage: 23,
  memory_usage: 41,
  disk_free: 82,
  models_loaded: 2,
  errors_last_hour: 0,
  uptime: "4h 23m",
  readiness: "operational",
};

export const mockModels = {
  model_2c: {
    name: "LightGBM 2-Classes",
    version: "v2.1",
    prediction: 1,
    labels: ["Queda", "Alta"],
    probabilities: [0.22, 0.78],
    confidence: 0.78,
    top_features: ["RSI_14", "MACD_signal", "MA20_slope", "Volume_ratio", "BB_width"],
    last_trained: "2026-06-15",
    recent_accuracy: 0.72,
  },
  model_3c: {
    name: "LightGBM 3-Classes",
    version: "v3.0",
    prediction: 2,
    labels: ["Venda", "Neutro", "Compra"],
    probabilities: [0.12, 0.18, 0.70],
    confidence: 0.70,
    top_features: ["RSI_14", "ATR_14", "MACD_histogram", "Candle_body_ratio", "STD_20"],
    last_trained: "2026-06-20",
    recent_accuracy: 0.68,
  },
  consensus: "BUY",
  consensus_confidence: 0.74,
  signal_quality: "Alta",
  signal_valid_until: "17:35",
};

export function getMarketSession() {
  const hour = new Date().getUTCHours();
  if (hour >= 0 && hour < 8) return "Ásia";
  if (hour >= 8 && hour < 16) return "Londres";
  return "Nova York";
}
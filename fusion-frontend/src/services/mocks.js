/**
 * Mock data layer — substituir por chamadas reais ao Fusion/MT5
 */

const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'AUDUSD', 'USDCAD'];
const TIMEFRAMES = ['M5', 'M15', 'M30', 'H1', 'H4'];
const STRATEGIES = ['S1_trend', 'S2_reversal', 'S3_breakout'];
const FILTER_NAMES = [
  'risk_engine', 'portfolio_correlation', 'portfolio_exposure', 'session_context',
  'timeframe_consensus', 'market_regime', 'macro_flow', 'market_structure',
  'candle_price_confirmation', 'ema_alignment', 'opportunity_engine', 'volatility_engine',
  'entry_timing', 'context_engine', 'context_brain', 'execution_engine',
  'manual_approval', 'allow_new_orders', 'mt5_autotrading', 'spread',
  'confidence', 'signal_strength',
];

function rnd(min, max, dec = 2) {
  return parseFloat((Math.random() * (max - min) + min).toFixed(dec));
}
function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function ts(minsAgo = 0) {
  return new Date(Date.now() - minsAgo * 60000).toISOString();
}

// ─── System Status ─────────────────────────────────────────────────────────
export function mockSystemStatus() {
  return {
    fusion: { status: 'online', last_cycle: ts(1), cycle_duration_ms: rnd(120, 890, 0) },
    mt5: { status: Math.random() > 0.1 ? 'online' : 'offline', account: '123456', server: 'MetaQuotes-Demo' },
    backend: { status: 'online', latency_ms: rnd(8, 45, 0) },
    feed: { status: 'online', last_candle: ts(0.3), candles_per_min: rnd(3, 12, 1) },
    symbols_monitored: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'],
    timeframes_monitored: ['M5', 'M15', 'H1'],
    open_orders: 3,
    last_signal: { symbol: 'EURUSD', direction: 'BUY', ts: ts(2) },
    last_order: { ticket: 98765, symbol: 'GBPUSD', ts: ts(8) },
    last_critical_error: null,
    simulated_latency_ms: rnd(12, 60, 0),
  };
}

// ─── Signals ───────────────────────────────────────────────────────────────
export function mockSignals(filters = {}) {
  const statuses = ['liberado', 'bloqueado', 'shadow', 'erro'];
  const decisions = ['BUY', 'SELL', 'WAIT'];
  const reasons = [
    'spread alto', 'regime bear', 'correlação alta', 'fora da sessão',
    'confluência baixa', 'modelo ausente', 'SL inválido', 'confiança < 0.6',
  ];
  let signals = Array.from({ length: 40 }, (_, i) => {
    const status = pick(statuses);
    const decision = pick(decisions);
    const p_buy = rnd(0.3, 0.9);
    const p_sell = parseFloat((1 - p_buy - rnd(0, 0.1)).toFixed(2));
    return {
      id: `sig_${i}_${Date.now()}`,
      symbol: pick(SYMBOLS),
      timeframe: pick(TIMEFRAMES),
      decision,
      p_buy,
      p_sell,
      confidence: rnd(0.5, 0.98),
      edge: rnd(0.01, 0.15),
      strategy: pick(STRATEGIES),
      status,
      reason: status !== 'liberado' ? pick(reasons) : '',
      timestamp: ts(rnd(0, 60, 0)),
    };
  });

  if (filters.symbol) signals = signals.filter(s => s.symbol === filters.symbol);
  if (filters.timeframe) signals = signals.filter(s => s.timeframe === filters.timeframe);
  if (filters.direction && filters.direction !== 'ALL') signals = signals.filter(s => s.decision === filters.direction);
  if (filters.status) signals = signals.filter(s => s.status === filters.status);
  if (filters.strategy) signals = signals.filter(s => s.strategy === filters.strategy);
  if (filters.min_confidence) signals = signals.filter(s => s.confidence >= parseFloat(filters.min_confidence));

  return signals.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

// ─── Filters ───────────────────────────────────────────────────────────────
export function mockFilters() {
  const modes = ['block', 'shadow', 'off'];
  const recs = ['manter block', 'virar shadow', 'desligar'];
  return FILTER_NAMES.map(name => ({
    name,
    mode: pick(modes),
    total_blocks: rnd(10, 500, 0),
    good_blocks: rnd(5, 300, 0),
    bad_blocks: rnd(0, 100, 0),
    profit_lost: rnd(0, 500, 2),
    loss_avoided: rnd(0, 800, 2),
    recommendation: pick(recs),
    last_reason: pick(['spread alto', 'regime bear', 'confluência fraca', 'fora da sessão', 'correlação alta']),
  }));
}

// ─── Runtime Control ───────────────────────────────────────────────────────
export function mockRuntimeControl() {
  return {
    trading_enabled: true,
    allow_new_orders: true,
    min_confidence_global: 0.65,
    min_signal_strength: 0.55,
    max_open_orders_total: 5,
    max_open_orders_per_symbol: 2,
    symbols_enabled: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'],
    symbols_disabled: ['BTCUSD'],
    timeframes_enabled: ['M5', 'M15', 'H1'],
    trailing_enabled: true,
    trailing_start_points: 20,
    trailing_step_points: 5,
    default_sl_points: 30,
    default_tp_points: 60,
    max_spread_points: 25,
    filter_modes: Object.fromEntries(FILTER_NAMES.map(n => [n, pick(['block', 'shadow', 'off'])])),
  };
}

// ─── Open Orders ───────────────────────────────────────────────────────────
export function mockOpenOrders() {
  const basePrice = { EURUSD: 1.0938, GBPUSD: 1.2745, USDJPY: 157.32, XAUUSD: 2341.5 };
  return Array.from({ length: 6 }, (_, i) => {
    const symbol = pick(['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']);
    const dir = pick(['BUY', 'SELL']);
    const entry = (basePrice[symbol] || 1.09) + rnd(-0.005, 0.005);
    const current = (basePrice[symbol] || 1.09) + rnd(-0.003, 0.008);
    const diff = dir === 'BUY' ? current - entry : entry - current;
    const lots = pick([0.01, 0.05, 0.1, 0.25]);
    return {
      ticket: 90000 + i,
      symbol,
      direction: dir,
      lots,
      entry_price: parseFloat(entry.toFixed(5)),
      current_price: parseFloat(current.toFixed(5)),
      sl: parseFloat((entry - (dir === 'BUY' ? 0.003 : -0.003)).toFixed(5)),
      tp: parseFloat((entry + (dir === 'BUY' ? 0.006 : -0.006)).toFixed(5)),
      profit: parseFloat((diff * lots * 100000).toFixed(2)),
      magic_number: 20240001 + i,
      strategy: pick(STRATEGIES),
      timeframe: pick(TIMEFRAMES),
      opened_at: ts(rnd(10, 300, 0)),
      trailing_active: Math.random() > 0.5,
      status: 'open',
    };
  });
}

// ─── Block Audit ───────────────────────────────────────────────────────────
export function mockBlockAudit() {
  return Array.from({ length: 30 }, (_, i) => {
    const dir = pick(['BUY', 'SELL']);
    const price = rnd(1.08, 1.11, 5);
    const after15 = price + (dir === 'BUY' ? rnd(-0.003, 0.008) : rnd(-0.008, 0.003));
    const after1h = price + (dir === 'BUY' ? rnd(-0.005, 0.015) : rnd(-0.015, 0.005));
    const after3h = price + (dir === 'BUY' ? rnd(-0.008, 0.022) : rnd(-0.022, 0.008));
    const result_pts = parseFloat(((dir === 'BUY' ? after3h - price : price - after3h) * 10000).toFixed(1));
    const good = result_pts < 0;
    return {
      id: `blk_${i}`,
      symbol: pick(SYMBOLS),
      timeframe: pick(TIMEFRAMES),
      direction: dir,
      filter: pick(FILTER_NAMES),
      price_at_block: parseFloat(price.toFixed(5)),
      price_after_15m: parseFloat(after15.toFixed(5)),
      price_after_1h: parseFloat(after1h.toFixed(5)),
      price_after_3h: parseFloat(after3h.toFixed(5)),
      result_points: result_pts,
      classification: good ? 'bom bloqueio' : 'mau bloqueio',
      profit_lost: good ? 0 : parseFloat(Math.abs(result_pts * 0.1 * 0.01).toFixed(2)),
      loss_avoided: good ? parseFloat(Math.abs(result_pts * 0.1 * 0.01).toFixed(2)) : 0,
      timestamp: ts(rnd(0, 1440, 0)),
    };
  });
}

// ─── Performance ───────────────────────────────────────────────────────────
export function mockPerformanceSummary() {
  return {
    by_symbol: SYMBOLS.map(s => ({
      symbol: s,
      profit: rnd(-200, 800, 2),
      win_rate: rnd(0.4, 0.75),
      total_orders: rnd(10, 80, 0),
      avg_points: rnd(-5, 25, 1),
      drawdown: rnd(0.02, 0.15),
    })),
    by_timeframe: TIMEFRAMES.map(tf => ({
      timeframe: tf,
      profit: rnd(-100, 500, 2),
      win_rate: rnd(0.4, 0.75),
      total_orders: rnd(5, 40, 0),
    })),
    by_strategy: STRATEGIES.map(st => ({
      strategy: st,
      profit: rnd(-150, 600, 2),
      win_rate: rnd(0.45, 0.72),
      total_orders: rnd(8, 50, 0),
    })),
    totals: {
      total_signals: 342,
      signals_blocked: 189,
      signals_executed: 153,
      total_profit: 1243.5,
      win_rate: 0.61,
      drawdown: 0.08,
    },
  };
}

export function mockFilterPerformance() {
  const recs = ['manter block', 'virar shadow', 'desligar'];
  return FILTER_NAMES.map(name => ({
    filter: name,
    total_blocks: rnd(10, 300, 0),
    good_blocks: rnd(5, 200, 0),
    bad_blocks: rnd(0, 80, 0),
    profit_lost: rnd(0, 400, 2),
    loss_avoided: rnd(0, 700, 2),
    recommendation: pick(recs),
  }));
}

// ─── Logs ──────────────────────────────────────────────────────────────────
const LOG_TYPES = ['sinal', 'ordem', 'bloqueio', 'erro', 'warning', 'timing'];
const LOG_MSGS = {
  sinal: ['BUY EURUSD M5 gerado | conf=0.71', 'SELL GBPUSD H1 gerado | conf=0.68', 'WAIT USDJPY M15 | conf baixa'],
  ordem: ['Ordem 90001 aberta EURUSD BUY 0.1', 'Ordem 90002 fechada GBPUSD SELL | profit=+12.3', 'Trailing ativado ticket 90003'],
  bloqueio: ['Bloqueado por spread alto (28pts)', 'Bloqueado por market_regime: bear', 'Shadow por timeframe_consensus'],
  erro: ['Erro MT5: conexão perdida', 'Modelo ausente XAUUSD H4', 'Timeout ao executar ordem'],
  warning: ['Spread alto XAUUSD (45pts)', 'Sem candle recente > 10min', 'Confiança abaixo do limiar global'],
  timing: ['Ciclo executado em 342ms', 'Features calculadas em 89ms', 'MT5 ping 24ms'],
};

export function mockLogs(filters = {}) {
  let logs = Array.from({ length: 80 }, (_, i) => {
    const type = pick(LOG_TYPES);
    return {
      id: `log_${i}`,
      timestamp: ts(rnd(0, 120, 1)),
      type,
      symbol: pick([...SYMBOLS, null]),
      timeframe: pick([...TIMEFRAMES, null]),
      message: pick(LOG_MSGS[type]),
      severity: type === 'erro' ? 'error' : type === 'warning' ? 'warn' : 'info',
    };
  });

  if (filters.type) logs = logs.filter(l => l.type === filters.type);
  if (filters.symbol) logs = logs.filter(l => !l.symbol || l.symbol === filters.symbol);
  if (filters.timeframe) logs = logs.filter(l => !l.timeframe || l.timeframe === filters.timeframe);
  if (filters.search) logs = logs.filter(l => l.message.toLowerCase().includes(filters.search.toLowerCase()));

  return logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

// ─── Model Registry ────────────────────────────────────────────────────────
export function mockModelRegistry() {
  const combos = [
    ['EURUSD', 'M5'], ['EURUSD', 'H1'], ['GBPUSD', 'M15'], ['GBPUSD', 'H1'],
    ['USDJPY', 'M5'], ['USDJPY', 'H4'], ['XAUUSD', 'M15'], ['XAUUSD', 'H1'],
    ['BTCUSD', 'H4'], ['AUDUSD', 'M5'],
  ];
  return combos.map(([symbol, tf]) => {
    const loaded = Math.random() > 0.15;
    return {
      id: `${symbol}_${tf}`,
      name: `fusion_${symbol}_${tf}`,
      symbol,
      timeframe: tf,
      path: `/models/${symbol}/${tf}/model_v2.pkl`,
      version: `2.${rnd(0, 5, 0)}.${rnd(0, 9, 0)}`,
      loaded,
      status: loaded ? (Math.random() > 0.1 ? 'aprovado' : 'reprovado') : 'ausente',
      last_prediction: loaded ? ts(rnd(0, 30, 0)) : null,
      avg_confidence: loaded ? rnd(0.6, 0.88) : null,
      error: !loaded ? 'FileNotFoundError: modelo não encontrado' : null,
    };
  });
}

// ─── Market Briefing ───────────────────────────────────────────────────────
export function mockMarketBriefing() {
  const valid_until = new Date(Date.now() + 4 * 3600000).toISOString();
  return {
    summary: 'Fed mantém hawkish, DXY em alta. EUR em pressão vendedora. Ouro lateraliza aguardando CPI.',
    risk_regime: 'risk_off',
    currency_bias: { USD: 'bullish', EUR: 'bearish', GBP: 'neutral', JPY: 'bullish', AUD: 'bearish' },
    pair_bias: { EURUSD: 'sell', GBPUSD: 'neutral', USDJPY: 'buy', XAUUSD: 'neutral' },
    asset_bias: { indices: 'bearish', commodities: 'neutral', crypto: 'bearish' },
    macro_rules: [
      'Evitar compras em EUR/GBP durante sessão americana',
      'Preferir venda de ouro em resistências',
      'USD favorecido em cruzamentos',
    ],
    valid_until,
    is_expired: new Date() > new Date(valid_until),
    last_updated: ts(30),
  };
}

// ─── Alerts ────────────────────────────────────────────────────────────────
export function mockAlerts() {
  return [
    { id: 'a1', type: 'mt5_disconnected', severity: 'error', message: 'MT5 perdeu conexão por 2min', timestamp: ts(15), acknowledged: false },
    { id: 'a2', type: 'spread_high', severity: 'warning', message: 'Spread XAUUSD = 45pts (limite 25)', timestamp: ts(8), acknowledged: false },
    { id: 'a3', type: 'model_missing', severity: 'warning', message: 'Modelo BTCUSD H4 não encontrado', timestamp: ts(45), acknowledged: true },
    { id: 'a4', type: 'no_candle', severity: 'warning', message: 'Sem candle AUDUSD M5 há 12min', timestamp: ts(12), acknowledged: false },
    { id: 'a5', type: 'order_rejected', severity: 'error', message: 'Ordem rejeitada pelo MT5: requote', timestamp: ts(3), acknowledged: false },
    { id: 'a6', type: 'autotrading_off', severity: 'error', message: 'MT5 AutoTrading desligado', timestamp: ts(1), acknowledged: false },
    { id: 'a7', type: 'fusion_no_cycle', severity: 'warning', message: 'Fusion sem novo ciclo há 8min', timestamp: ts(8), acknowledged: false },
  ];
}

// ─── Chart Overlays ────────────────────────────────────────────────────────
export function mockChartOverlays(symbol, timeframe) {
  return {
    symbol, timeframe,
    entries: [{ price: 1.0912, direction: 'BUY', ts: ts(30) }, { price: 1.0955, direction: 'SELL', ts: ts(10) }],
    exits: [{ price: 1.0945, profit: 33, ts: ts(20) }],
    sl_levels: [{ price: 1.0885 }, { price: 1.0975 }],
    tp_levels: [{ price: 1.0960 }, { price: 1.0870 }],
    support_resistance: [{ price: 1.0890, type: 'support' }, { price: 1.0965, type: 'resistance' }],
    signals: [{ price: 1.0920, direction: 'BUY', blocked: false, ts: ts(25) }, { price: 1.0950, direction: 'SELL', blocked: true, reason: 'spread alto', ts: ts(15) }],
  };
}
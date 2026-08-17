/**
 * Mock do FusionSignalPanel — representa o que o FusionSignalPanel.mq5 envia
 * Substituir por chamada real ao Fusion quando disponível
 */

function rnd(min, max, dec = 5) {
  return parseFloat((Math.random() * (max - min) + min).toFixed(dec));
}

export function mockFusionSignalPanel(symbol = 'EURUSD', timeframe = 'M15') {
  const signals = ['BUY', 'SELL', 'WAIT'];
  const statuses = ['allowed', 'blocked', 'shadow', 'wait', 'no_signal'];
  const signal = signals[Math.floor(Math.random() * signals.length)];
  const status = signal === 'WAIT' ? 'wait' : statuses[Math.floor(Math.random() * 3)];

  const basePrices = {
    EURUSD: 1.09625, GBPUSD: 1.27450, USDJPY: 157.32,
    gold: 2341.50, GBPJPY: 200.15, AUDCAD: 0.9120,
    USDCAD: 1.3620, AUDNZD: 1.0850, EURGBP: 0.8520,
  };
  const base = basePrices[symbol] || 1.09625;
  const entry = parseFloat((base + rnd(-0.001, 0.001)).toFixed(5));
  const sl = parseFloat((entry - (signal === 'BUY' ? rnd(0.0005, 0.002) : -rnd(0.0005, 0.002))).toFixed(5));
  const tp = parseFloat((entry + (signal === 'BUY' ? rnd(0.001, 0.004) : -rnd(0.001, 0.004))).toFixed(5));

  const reasons = {
    allowed: ['Confluência multi-TF confirmada', 'S2 ensemble aprovado', 'Tendência H1 alinhada', 'Setup de pullback válido'],
    blocked: ['Bloqueado por spread alto', 'Regime de mercado: bear', 'Correlação alta no portfólio', 'Fora da sessão'],
    shadow: ['Shadow por timeframe_consensus', 'Shadow: macro_flow negativo', 'Monitorando sem executar'],
    wait: ['Aguardando confirmação de candle', 'Aguardando fechamento M15', 'Borda insuficiente'],
    no_signal: ['Sem sinal neste momento', 'Confiança abaixo do limiar'],
  };

  return {
    symbol,
    timeframe,
    signal: signal,
    status,
    confidence: Math.floor(rnd(30, 92, 0)),
    analysis_time: new Date().toTimeString().slice(0, 8),
    entry,
    stop_loss: sl,
    take_profit: tp,
    support_levels: [
      parseFloat((entry - rnd(0.001, 0.003)).toFixed(5)),
      parseFloat((entry - rnd(0.003, 0.006)).toFixed(5)),
    ],
    resistance_levels: [
      parseFloat((entry + rnd(0.001, 0.003)).toFixed(5)),
      parseFloat((entry + rnd(0.003, 0.006)).toFixed(5)),
    ],
    reason: (reasons[status] || reasons.wait)[Math.floor(Math.random() * (reasons[status] || reasons.wait).length)],
    strategy: ['S1', 'S2', 'S3', 'S6'][Math.floor(Math.random() * 4)],
    p_buy: parseFloat(rnd(0.2, 0.85, 2).toFixed(2)),
    p_sell: parseFloat(rnd(0.1, 0.75, 2).toFixed(2)),
    updated_at: new Date().toISOString(),
    filter_summary: {
      passed: Math.floor(rnd(4, 12, 0)),
      blocked_by: status === 'blocked' ? ['volatility_engine', 'market_alignment'][Math.floor(Math.random() * 2)] : null,
      shadow_by: status === 'shadow' ? 'macro_flow' : null,
    },
    // historical decision gate mock (observability only)
    historical_decision: {
      decision: Math.random() > 0.7 ? 'hold' : (Math.random() > 0.5 ? 'buy' : 'sell'),
      confidence: Math.floor(rnd(30, 95, 0)),
      reasons: ['profile_zone_ok', 'recency_aligned'].slice(0, Math.floor(Math.random() * 3) + 1),
      details: { acceptance_status: Math.random() > 0.5 ? 'accepted' : 'needs_validation' },
    },
  };
}

export function mockFusionChartOverlay(symbol = 'EURUSD', timeframe = 'M15') {
  const panel = mockFusionSignalPanel(symbol, timeframe);
  return {
    symbol,
    timeframe,
    signal_arrow: {
      price: panel.entry,
      direction: panel.signal,
      status: panel.status,
      reason: panel.reason,
      ts: panel.updated_at,
    },
    entry_line: { price: panel.entry, label: 'Entrada' },
    sl_line: { price: panel.stop_loss, label: 'SL' },
    tp_line: { price: panel.take_profit, label: 'TP' },
    support_levels: panel.support_levels.map((p, i) => ({ price: p, label: `S${i + 1}` })),
    resistance_levels: panel.resistance_levels.map((p, i) => ({ price: p, label: `R${i + 1}` })),
    updated_at: panel.updated_at,
  };
}
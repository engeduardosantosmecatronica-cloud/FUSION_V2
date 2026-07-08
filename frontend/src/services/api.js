/**
 * API Service Layer
 * Contratos de API futuros — trocar mocks por chamadas reais ao Fusion/MT5
 * Todos os métodos retornam Promise<T>
 */
import {
  mockSystemStatus, mockSignals, mockFilters, mockRuntimeControl,
  mockOpenOrders, mockBlockAudit, mockPerformanceSummary, mockFilterPerformance,
  mockLogs, mockModelRegistry, mockMarketBriefing, mockAlerts, mockChartOverlays,
} from './mocks';

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms));

export const getSystemStatus = async () => { await delay(200); return mockSystemStatus(); };
export const getLiveSignals = async (filters = {}) => { await delay(300); return mockSignals(filters); };
export const getDecisionTimeline = async (signalId) => {
  await delay(400);
  const signals = mockSignals({});
  const s = signals.find(x => x.id === signalId) || signals[0];
  return {
    signal: s,
    candle: { open: 1.0935, high: 1.0942, low: 1.0928, close: 1.0938, volume: 3241 },
    features: { rsi: 58.2, ema_slope: 0.0003, atr: 0.0012, volume_ratio: 1.34 },
    model: { name: `fusion_${s?.symbol}_${s?.timeframe}`, version: '2.1.0' },
    p_buy: s?.p_buy, p_sell: s?.p_sell,
    filters_applied: mockFilters().slice(0, 8).map(f => ({ name: f.name, mode: f.mode, passed: f.mode !== 'block' || Math.random() > 0.3 })),
    strategy: s?.strategy, decision: s?.decision,
    order_attempt: s?.status === 'liberado' ? { sent: true, ticket: 98765 } : { sent: false, reason: s?.reason },
    mt5_result: s?.status === 'liberado' ? 'accepted' : 'not_sent',
  };
};
export const getFilterStatus = async () => { await delay(250); return mockFilters(); };
export const updateFilterMode = async (filterName, mode) => { await delay(200); return { filterName, mode, updated: true }; };
export const getRuntimeControl = async () => { await delay(200); return mockRuntimeControl(); };
export const updateRuntimeControl = async (payload) => { await delay(300); return { ...mockRuntimeControl(), ...payload }; };
export const getOpenOrders = async () => { await delay(300); return mockOpenOrders(); };
export const closeOrder = async (ticket, partial = false, lots = null) => { await delay(400); return { ok: true, ticket, partial, lots, message: `Ordem ${ticket} fechada (simulado)` }; };
export const updateOrder = async (ticket, payload) => { await delay(300); return { ok: true, ticket, ...payload }; };
export const getBlockAudit = async (filters = {}) => { await delay(350); return mockBlockAudit(filters); };
export const getPerformanceSummary = async () => { await delay(300); return mockPerformanceSummary(); };
export const getFilterPerformance = async () => { await delay(300); return mockFilterPerformance(); };
export const getLogs = async (filters = {}) => { await delay(250); return mockLogs(filters); };
export const getModelRegistry = async () => { await delay(300); return mockModelRegistry(); };
export const getMarketBriefing = async () => { await delay(250); return mockMarketBriefing(); };
export const updateMarketBriefing = async (payload) => { await delay(300); return { ...mockMarketBriefing(), ...payload }; };
export const getAlerts = async () => { await delay(200); return mockAlerts(); };
export const acknowledgeAlert = async (alertId) => { await delay(200); return { ok: true, alertId }; };
export const getChartOverlays = async (symbol, timeframe) => { await delay(200); return mockChartOverlays(symbol, timeframe); };
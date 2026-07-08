/**
 * API Service Layer
 * Usa a API local do Fusion/MT5 quando disponivel e cai para mocks se ela estiver offline.
 */
import {
  mockSystemStatus, mockSignals, mockFilters, mockRuntimeControl,
  mockOpenOrders, mockBlockAudit, mockPerformanceSummary, mockFilterPerformance,
  mockLogs, mockModelRegistry, mockMarketBriefing, mockAlerts, mockChartOverlays,
} from './mocks';

const API_BASE = import.meta.env.VITE_FUSION_API_BASE_URL || import.meta.env.VITE_MT5_API_BASE_URL || 'http://127.0.0.1:5000';

function qs(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value);
  });
  return params.toString();
}

async function requestJson(path, options = {}) {
  const response = await fetch(new URL(path, API_BASE), {
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(`Fusion API ${response.status}: ${await response.text().catch(() => response.statusText)}`);
  return response.json();
}

async function withFallback(call, fallback) {
  try { return await call(); }
  catch (error) {
    console.warn('[Fusion API fallback]', error?.message || error);
    return typeof fallback === 'function' ? fallback() : fallback;
  }
}

export const getSystemStatus = async () => withFallback(() => requestJson('/api/fusion/status'), mockSystemStatus);
export const getLiveSignals = async (filters = {}) => withFallback(() => requestJson(`/api/fusion/signals?${qs(filters)}`), () => mockSignals(filters));
export const getDecisionTimeline = async (signalId) => withFallback(() => requestJson(`/api/fusion/decision-timeline?signalId=${encodeURIComponent(signalId || '')}`), async () => {
  const signals = mockSignals({});
  const s = signals.find(x => x.id === signalId) || signals[0];
  return { signal: s, filters_applied: mockFilters().slice(0, 8), decision: s?.decision || 'WAIT' };
});
export const getFilterStatus = async () => withFallback(() => requestJson('/api/fusion/filters'), mockFilters);
export const updateFilterMode = async (filterName, mode) => withFallback(
  () => requestJson('/api/fusion/filter-mode', { method: 'POST', body: JSON.stringify({ filterName, mode }) }),
  { filterName, mode, updated: false }
);
export const getRuntimeControl = async () => withFallback(() => requestJson('/api/fusion/runtime'), mockRuntimeControl);
export const updateRuntimeControl = async (payload) => withFallback(
  () => requestJson('/api/fusion/runtime', { method: 'PUT', body: JSON.stringify(payload) }),
  () => ({ ...mockRuntimeControl(), ...payload })
);
export const getOpenOrders = async () => withFallback(() => requestJson('/api/fusion/orders'), mockOpenOrders);
export const closeOrder = async (ticket, partial = false, lots = null) => withFallback(
  () => requestJson('/api/fusion/order/close', { method: 'POST', body: JSON.stringify({ ticket, partial, lots }) }),
  { ok: false, ticket, partial, lots, message: `Ordem ${ticket} nao enviada: API indisponivel` }
);
export const updateOrder = async (ticket, payload) => withFallback(
  () => requestJson('/api/fusion/order/update', { method: 'POST', body: JSON.stringify({ ticket, ...payload }) }),
  { ok: false, ticket, ...payload }
);
export const getBlockAudit = async (filters = {}) => withFallback(() => requestJson(`/api/fusion/block-audit?${qs(filters)}`), () => mockBlockAudit(filters));
export const getPerformanceSummary = async () => withFallback(() => requestJson('/api/fusion/performance'), mockPerformanceSummary);
export const getFilterPerformance = async () => withFallback(() => requestJson('/api/fusion/filter-performance'), mockFilterPerformance);
export const getLogs = async (filters = {}) => withFallback(() => requestJson(`/api/fusion/logs?${qs(filters)}`), () => mockLogs(filters));
export const getModelRegistry = async () => withFallback(() => requestJson('/api/fusion/models'), mockModelRegistry);
export const getMarketBriefing = async () => withFallback(() => requestJson('/api/fusion/briefing'), mockMarketBriefing);
export const updateMarketBriefing = async (payload) => withFallback(
  () => requestJson('/api/fusion/briefing', { method: 'PUT', body: JSON.stringify(payload) }),
  () => ({ ...mockMarketBriefing(), ...payload })
);
export const getAlerts = async () => withFallback(() => requestJson('/api/fusion/alerts'), mockAlerts);
export const acknowledgeAlert = async (alertId) => withFallback(
  () => requestJson('/api/fusion/alert/ack', { method: 'POST', body: JSON.stringify({ alertId }) }),
  { ok: false, alertId }
);
export const getChartOverlays = async (symbol, timeframe) => withFallback(
  () => requestJson(`/api/fusion/chart-overlays?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`),
  () => mockChartOverlays(symbol, timeframe)
);

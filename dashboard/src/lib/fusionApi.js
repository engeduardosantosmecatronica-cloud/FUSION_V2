const API_BASE = import.meta.env.VITE_FUSION_API_URL || "http://127.0.0.1:5000";
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  if (!response.ok) throw new Error(`Fusion API ${response.status}`);
  return response.json();
}
export const fusionApi = {
  candles: (symbol, timeframe, limit = 300) => request(`/api/candles?${new URLSearchParams({ symbol, tf: timeframe, limit: String(limit) })}`),
  live: (symbol, timeframe) => request(`/api/live?${new URLSearchParams({ symbol, tf: timeframe })}`),
  selectStream: (symbol, timeframe, limit = 500) => request("/api/stream", { method: "POST", body: JSON.stringify({ symbol, timeframe, limit }) }),
  health: () => request("/api/health"),
  status: () => request("/api/fusion/status"),
  runtime: () => request("/api/fusion/runtime"),
  updateRuntime: (payload) => request("/api/fusion/runtime", { method: "POST", body: JSON.stringify(payload) }),
  patchRuntime: (path, value) => request("/api/fusion/runtime/patch", { method: "POST", body: JSON.stringify({ path, value }) }),
  orders: () => request("/api/fusion/orders"),
  closeOrder: (ticket, partial = false, lots) => request("/api/fusion/order/close", { method: "POST", body: JSON.stringify({ ticket, partial, lots }) }),
  updateOrder: (ticket, changes) => request("/api/fusion/order/update", { method: "POST", body: JSON.stringify({ ticket, ...changes }) }),
  logs: () => request("/api/fusion/logs"),
  alerts: () => request("/api/fusion/alerts"),
  models: () => request("/api/fusion/models"),
  performance: () => request("/api/fusion/performance"),
  signals: () => request("/api/fusion/signals"),
  filters: () => request("/api/fusion/filters"),
};
export { API_BASE };

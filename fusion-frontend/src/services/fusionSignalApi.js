/** Fusion Signal Panel API real com fallback mockado. */
import { mockFusionSignalPanel } from '@/mocks/fusionSignalPanelMock';

const API_BASE = import.meta.env.VITE_FUSION_API_BASE_URL || import.meta.env.VITE_MT5_API_BASE_URL || 'http://127.0.0.1:5000';

async function requestJson(path) {
  const response = await fetch(new URL(path, API_BASE), { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Fusion API ${response.status}`);
  return response.json();
}

export async function getFusionSignalPanel(symbol, timeframe) {
  try {
    return await requestJson(`/api/fusion/signal-panel?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`);
  } catch (error) {
    console.warn('[Fusion Signal fallback]', error?.message || error);
    return mockFusionSignalPanel(symbol, timeframe);
  }
}

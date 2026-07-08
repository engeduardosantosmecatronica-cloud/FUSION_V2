/**
 * fusionChartApi — contrato de API para overlays no gráfico
 * Endpoint futuro: GET http://localhost:5000/api/chart-overlay?symbol=EURUSD&timeframe=M15
 */
import { mockFusionChartOverlay } from '@/mocks/fusionSignalPanelMock';

const delay = (ms = 150) => new Promise(r => setTimeout(r, ms));

export async function getFusionChartOverlays(symbol, timeframe) {
  await delay(150);
  return mockFusionChartOverlay(symbol, timeframe);
  // FUTURO: return (await fetch(`/api/chart-overlay?symbol=${symbol}&timeframe=${timeframe}`)).json();
}
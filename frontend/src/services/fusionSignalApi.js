/**
 * fusionSignalApi — contrato de API para o painel de sinais do Fusion
 * Endpoint futuro: GET http://localhost:5000/api/signal-panel?symbol=EURUSD&timeframe=M15
 */
import { mockFusionSignalPanel } from '@/mocks/fusionSignalPanelMock';

const delay = (ms = 200) => new Promise(r => setTimeout(r, ms));

export async function getFusionSignalPanel(symbol, timeframe) {
  await delay(200);
  return mockFusionSignalPanel(symbol, timeframe);
  // FUTURO: return (await fetch(`/api/signal-panel?symbol=${symbol}&timeframe=${timeframe}`)).json();
}
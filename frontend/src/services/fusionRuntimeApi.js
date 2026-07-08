/**
 * fusionRuntimeApi — contrato de API para o Fusion Runtime Control
 * Trocar as implementações por chamadas HTTP reais ao Fusion quando disponível
 *
 * Endpoint base futuro: GET/POST/PATCH http://localhost:5000/api/runtime
 */
import { mockFusionRuntimeControl, mockFusionConfigSchema } from '@/mocks/fusionRuntimeMock';

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms));

/** Carrega o runtime control completo */
export async function getFusionRuntimeControl() {
  await delay(250);
  return mockFusionRuntimeControl();
  // FUTURO: return (await fetch('/api/runtime')).json();
}

/** Salva o runtime control completo */
export async function updateFusionRuntimeControl(payload) {
  await delay(350);
  return { ok: true, saved: payload };
  // FUTURO: return (await fetch('/api/runtime', { method: 'PUT', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } })).json();
}

/** Aplica patch em um campo específico (path estilo dot-notation) */
export async function patchFusionRuntimeControl(path, value) {
  await delay(200);
  return { ok: true, path, value };
  // FUTURO: return (await fetch('/api/runtime/patch', { method: 'PATCH', body: JSON.stringify({ path, value }), headers: { 'Content-Type': 'application/json' } })).json();
}

/** Valida o payload antes de salvar */
export async function validateFusionRuntimeControl(payload) {
  await delay(200);
  const errors = [];
  if (!payload.enabled === undefined) errors.push({ path: 'enabled', message: 'Campo obrigatório' });
  if (payload.signal?.buy_threshold > 1) errors.push({ path: 'signal.buy_threshold', message: 'Deve ser entre 0 e 1' });
  if (payload.signal?.sell_threshold > 1) errors.push({ path: 'signal.sell_threshold', message: 'Deve ser entre 0 e 1' });
  return { valid: errors.length === 0, errors };
}

/** Retorna o schema de configuração */
export async function getFusionConfigSchema() {
  await delay(150);
  return mockFusionConfigSchema();
}

/** Retorna o diff entre configuração atual e rascunho */
export async function getFusionConfigDiff(current, draft) {
  await delay(200);
  const diff = [];
  const compare = (a, b, path = '') => {
    if (typeof a !== typeof b || typeof a !== 'object' || a === null || b === null) {
      if (JSON.stringify(a) !== JSON.stringify(b)) {
        diff.push({ path, from: a, to: b });
      }
      return;
    }
    const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
    keys.forEach(k => compare(a?.[k], b?.[k], path ? `${path}.${k}` : k));
  };
  compare(current, draft);
  return diff;
}

/** Exporta o runtime control como JSON string */
export async function exportFusionRuntimeControl() {
  const data = await getFusionRuntimeControl();
  return JSON.stringify(data, null, 2);
}

/** Importa o runtime control de um JSON string */
export async function importFusionRuntimeControl(jsonString) {
  await delay(200);
  const parsed = JSON.parse(jsonString);
  return parsed;
}

/** Aplica um preset predefinido */
export async function applyFusionPreset(presetName) {
  await delay(300);
  const presets = {
    conservador: { 'signal.buy_threshold': 0.72, 'signal.sell_threshold': 0.72, 'signal.confidence_filter': 0.75, 'risk.max_positions': 2, 'trailing.enabled': false },
    normal: { 'signal.buy_threshold': 0.55, 'signal.sell_threshold': 0.55, 'signal.confidence_filter': 0.60, 'risk.max_positions': 5, 'trailing.enabled': true },
    agressivo: { 'signal.buy_threshold': 0.45, 'signal.sell_threshold': 0.45, 'signal.confidence_filter': 0.50, 'risk.max_positions': 10, 'trailing.enabled': true },
    diagnostico: { 'trading.allow_new_orders': false, 'signal.buy_threshold': 0.35, 'signal.confidence_filter': 0.40, 'risk.max_positions': 1 },
    monitor_only: { 'trading.allow_new_orders': false, 'trading.execution_mode': 'monitor', 'risk.max_positions': 0 },
  };
  return presets[presetName] || {};
}
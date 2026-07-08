/** Runtime/config service ligado ao Fusion local. */
import { mockFusionRuntimeControl } from '@/mocks/fusionRuntimeMock';


const LOCAL_PRESETS = [
  {
    name: 'operacao_equilibrada',
    label: 'Operacao equilibrada',
    patch: { trading: { allow_new_orders: true }, signal: { confidence_filter: 0.58, min_signal_strength: 0.45 } },
    patches: [
      ['trading.allow_new_orders', true],
      ['signal.confidence_filter', 0.58],
      ['signal.min_signal_strength', 0.45],
    ],
  },
  {
    name: 'mais_conservador',
    label: 'Mais conservador',
    patch: { signal: { confidence_filter: 0.65, min_signal_strength: 0.55 } },
    patches: [
      ['signal.confidence_filter', 0.65],
      ['signal.min_signal_strength', 0.55],
    ],
  },
  {
    name: 'mais_agressivo',
    label: 'Mais agressivo',
    patch: { signal: { confidence_filter: 0.52, min_signal_strength: 0.35 } },
    patches: [
      ['signal.confidence_filter', 0.52],
      ['signal.min_signal_strength', 0.35],
    ],
  },
];
const API_BASE = import.meta.env.VITE_FUSION_API_BASE_URL || import.meta.env.VITE_MT5_API_BASE_URL || 'http://127.0.0.1:5000';

async function requestJson(path, options = {}) {
  const response = await fetch(new URL(path, API_BASE), {
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Fusion API ${response.status}: ${await response.text().catch(() => response.statusText)}`);
  }
  return response.json();
}

async function withFallback(call, fallback) {
  try {
    return await call();
  } catch (error) {
    console.warn('[Fusion runtime fallback]', error?.message || error);
    return typeof fallback === 'function' ? fallback() : fallback;
  }
}

function diffObjects(from, to, prefix = '') {
  const out = [];
  const keys = new Set([...Object.keys(from || {}), ...Object.keys(to || {})]);
  keys.forEach((key) => {
    if (key === '_meta') return;
    const path = prefix ? `${prefix}.${key}` : key;
    const a = from?.[key];
    const b = to?.[key];
    const bothObjects = a && b && typeof a === 'object' && typeof b === 'object' && !Array.isArray(a) && !Array.isArray(b);
    if (bothObjects) {
      out.push(...diffObjects(a, b, path));
      return;
    }
    if (JSON.stringify(a) !== JSON.stringify(b)) {
      out.push({ path, from: a, to: b });
    }
  });
  return out;
}

export async function getFusionRuntimeControl() {
  return withFallback(() => requestJson('/api/fusion/runtime'), mockFusionRuntimeControl);
}

export async function updateFusionRuntimeControl(payload) {
  return withFallback(
    () => requestJson('/api/fusion/runtime', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
    () => ({ ...mockFusionRuntimeControl(), ...payload, _mock: true }),
  );
}

export async function patchFusionRuntimeControl(path, value) {
  return withFallback(
    () => requestJson('/api/fusion/runtime/patch', {
      method: 'PATCH',
      body: JSON.stringify({ path, value }),
    }),
    () => ({ ...mockFusionRuntimeControl(), _mock: true }),
  );
}

export async function getFusionConfigDiff(original = {}, draft = {}) {
  return diffObjects(original, draft);
}

export async function exportFusionRuntimeControl() {
  const control = await getFusionRuntimeControl();
  return JSON.stringify(control, null, 2);
}

export async function importFusionRuntimeControl(text) {
  const parsed = JSON.parse(text);
  return updateFusionRuntimeControl(parsed);
}

export async function applyFusionPreset(name) {
  const presets = LOCAL_PRESETS;
  const preset = presets.find((item) => item.name === name);
  if (!preset) return [];
  const control = await getFusionRuntimeControl();
  const next = {
    ...control,
    ...(preset.patch || {}),
    _meta: undefined,
  };
  await updateFusionRuntimeControl(next);
  return preset.patches || [];
}

export async function getFusionPresets() {
  return LOCAL_PRESETS;
}


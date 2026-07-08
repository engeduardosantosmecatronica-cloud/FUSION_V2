import { useEffect, useState } from 'react';
import { getRuntimeControl, updateRuntimeControl } from '@/services/api';
import { cn } from '@/lib/utils';
import { AlertTriangle, Save, RotateCcw } from 'lucide-react';

const FILTER_NAMES = [
  'risk_engine','portfolio_correlation','portfolio_exposure','session_context',
  'timeframe_consensus','market_regime','macro_flow','market_structure',
  'candle_price_confirmation','ema_alignment','opportunity_engine','volatility_engine',
  'entry_timing','context_engine','context_brain','execution_engine',
  'manual_approval','allow_new_orders','mt5_autotrading','spread','confidence','signal_strength',
];

const PRESETS = {
  Conservador: { min_confidence_global: 0.80, min_signal_strength: 0.75, max_open_orders_total: 2, trailing_enabled: false, default_sl_points: 20, default_tp_points: 40, max_spread_points: 15 },
  Normal: { min_confidence_global: 0.65, min_signal_strength: 0.55, max_open_orders_total: 5, trailing_enabled: true, default_sl_points: 30, default_tp_points: 60, max_spread_points: 25 },
  Agressivo: { min_confidence_global: 0.52, min_signal_strength: 0.45, max_open_orders_total: 10, trailing_enabled: true, default_sl_points: 40, default_tp_points: 80, max_spread_points: 35 },
  Diagnóstico: { min_confidence_global: 0.40, min_signal_strength: 0.30, max_open_orders_total: 1, trading_enabled: false, allow_new_orders: false },
  'Somente monitoramento': { trading_enabled: false, allow_new_orders: false, max_open_orders_total: 0 },
};

function Field({ label, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-border">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

function Toggle({ value, onChange }) {
  return (
    <button onClick={() => onChange(!value)}
      className={cn('text-xs px-3 py-1 rounded border font-medium', value ? 'border-green-600 text-green-400' : 'border-border text-muted-foreground')}>
      {value ? 'ON' : 'OFF'}
    </button>
  );
}

export default function RuntimeControl() {
  const [config, setConfig] = useState(null);
  const [original, setOriginal] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getRuntimeControl().then(c => { setConfig(c); setOriginal(c); });
  }, []);

  const applyPreset = (name) => {
    setConfig(c => ({ ...c, ...PRESETS[name] }));
  };

  const save = async () => {
    setSaving(true);
    await updateRuntimeControl(config);
    setOriginal(config);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const restore = () => setConfig(original);

  const set = (key, val) => setConfig(c => ({ ...c, [key]: val }));
  const setNum = (key, val) => set(key, parseFloat(val));

  if (!config) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  const hasDiff = JSON.stringify(config) !== JSON.stringify(original);

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Runtime Control</h1>
        <span className="text-xs text-yellow-400 flex items-center gap-1"><AlertTriangle size={10} /> MOCK MODE</span>
      </div>

      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-muted-foreground self-center">Presets:</span>
        {Object.keys(PRESETS).map(p => (
          <button key={p} onClick={() => applyPreset(p)}
            className="text-xs px-3 py-1 bg-secondary border border-border rounded hover:bg-accent">{p}</button>
        ))}
      </div>

      {hasDiff && (
        <div className="text-xs text-yellow-400 flex items-center gap-1 border border-yellow-800 rounded px-2 py-1">
          <AlertTriangle size={10} /> Há alterações não salvas
        </div>
      )}

      <div className="bg-card border border-border rounded p-4 space-y-0">
        <div className="text-xs font-bold text-muted-foreground uppercase mb-2">Geral</div>
        <Field label="trading_enabled"><Toggle value={config.trading_enabled} onChange={v => set('trading_enabled', v)} /></Field>
        <Field label="allow_new_orders"><Toggle value={config.allow_new_orders} onChange={v => set('allow_new_orders', v)} /></Field>
        <Field label="trailing_enabled"><Toggle value={config.trailing_enabled} onChange={v => set('trailing_enabled', v)} /></Field>
        <Field label="min_confidence_global">
          <input type="number" step="0.01" min="0" max="1" value={config.min_confidence_global}
            onChange={e => setNum('min_confidence_global', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="min_signal_strength">
          <input type="number" step="0.01" min="0" max="1" value={config.min_signal_strength}
            onChange={e => setNum('min_signal_strength', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="max_open_orders_total">
          <input type="number" min="0" value={config.max_open_orders_total}
            onChange={e => setNum('max_open_orders_total', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="max_open_orders_per_symbol">
          <input type="number" min="0" value={config.max_open_orders_per_symbol}
            onChange={e => setNum('max_open_orders_per_symbol', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="default_sl_points">
          <input type="number" min="0" value={config.default_sl_points}
            onChange={e => setNum('default_sl_points', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="default_tp_points">
          <input type="number" min="0" value={config.default_tp_points}
            onChange={e => setNum('default_tp_points', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="max_spread_points">
          <input type="number" min="0" value={config.max_spread_points}
            onChange={e => setNum('max_spread_points', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="trailing_start_points">
          <input type="number" min="0" value={config.trailing_start_points}
            onChange={e => setNum('trailing_start_points', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
        <Field label="trailing_step_points">
          <input type="number" min="0" value={config.trailing_step_points}
            onChange={e => setNum('trailing_step_points', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right" />
        </Field>
      </div>

      {/* Filter modes */}
      <div className="bg-card border border-border rounded p-4">
        <div className="text-xs font-bold text-muted-foreground uppercase mb-3">Modos dos Filtros</div>
        <div className="grid grid-cols-2 gap-2">
          {FILTER_NAMES.map(name => (
            <div key={name} className="flex items-center justify-between gap-2">
              <span className="text-xs font-mono text-muted-foreground truncate">{name}</span>
              <select value={config.filter_modes?.[name] || 'off'}
                onChange={e => setConfig(c => ({ ...c, filter_modes: { ...c.filter_modes, [name]: e.target.value } }))}
                className="bg-secondary border border-border rounded px-1 py-0.5 text-xs">
                <option value="block">block</option>
                <option value="shadow">shadow</option>
                <option value="off">off</option>
              </select>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={save} disabled={saving}
          className="flex items-center gap-1 text-xs px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50">
          <Save size={12} /> {saving ? 'Salvando...' : saved ? 'Salvo!' : 'Salvar'}
        </button>
        <button onClick={restore}
          className="flex items-center gap-1 text-xs px-4 py-2 bg-secondary border border-border rounded hover:bg-accent">
          <RotateCcw size={12} /> Restaurar Padrão
        </button>
      </div>
    </div>
  );
}
import { useState } from 'react';
import { Field, Toggle, NumInput, Section } from '../FusionFieldRenderers';

function SymbolTPSLEditor({ data, onChange }) {
  const [sym, setSym] = useState('');
  const entries = Object.entries(data || {});
  const add = () => {
    if (sym.trim() && !data[sym.trim()]) {
      onChange({ ...data, [sym.trim()]: { tp_points: 60, sl_points: 30 } });
      setSym('');
    }
  };
  return (
    <div className="space-y-1">
      {entries.map(([s, v]) => (
        <div key={s} className="flex items-center gap-2">
          <span className="font-bold w-16 text-xs">{s}</span>
          <span className="text-xs text-muted-foreground">TP</span>
          <input type="number" step="1" value={v.tp_points} onChange={e => onChange({ ...data, [s]: { ...v, tp_points: parseInt(e.target.value) } })} className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-16 font-mono" />
          <span className="text-xs text-muted-foreground">SL</span>
          <input type="number" step="1" value={v.sl_points} onChange={e => onChange({ ...data, [s]: { ...v, sl_points: parseInt(e.target.value) } })} className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-16 font-mono" />
          <button onClick={() => { const n = { ...data }; delete n[s]; onChange(n); }} className="text-xs text-red-400">×</button>
        </div>
      ))}
      <div className="flex gap-1 mt-1">
        <input value={sym} onChange={e => setSym(e.target.value)} placeholder="Símbolo" className="bg-secondary border border-border rounded px-2 py-0.5 text-xs w-24" />
        <button onClick={add} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">+</button>
      </div>
    </div>
  );
}

export default function TabTrailing({ draft, set }) {
  const tr = draft.trailing || {};
  const rt = draft.runtime || {};
  const updTr = (k, v) => set('trailing', { ...tr, [k]: v });
  const updGTP = (k, v) => set('runtime', { ...rt, global_tp_sl: { ...(rt.global_tp_sl || {}), [k]: v } });
  const updRBS = (sym, k, v) => set('runtime', { ...rt, risk_by_symbol: { ...(rt.risk_by_symbol || {}), [sym]: { ...(rt.risk_by_symbol?.[sym] || {}), [k]: v } } });

  return (
    <div className="space-y-2">
      <Section title="Trailing Stop">
        <Field label="enabled"><Toggle value={tr.enabled} onChange={v => updTr('enabled', v)} /></Field>
        <Field label="activation_pips"><NumInput value={tr.activation_pips} onChange={v => updTr('activation_pips', v)} step={1} small /></Field>
        <Field label="distance_pips"><NumInput value={tr.distance_pips} onChange={v => updTr('distance_pips', v)} step={1} small /></Field>
        <Field label="check_interval" unit="s"><NumInput value={tr.check_interval} onChange={v => updTr('check_interval', v)} step={1} unit="s" small /></Field>
      </Section>

      <Section title="Runtime Global TP/SL">
        <Field label="use_runtime_override"><Toggle value={rt.global_tp_sl?.use_runtime_override} onChange={v => updGTP('use_runtime_override', v)} /></Field>
        <Field label="tp_points"><NumInput value={rt.global_tp_sl?.tp_points} onChange={v => updGTP('tp_points', v)} step={1} small /></Field>
        <Field label="sl_points"><NumInput value={rt.global_tp_sl?.sl_points} onChange={v => updGTP('sl_points', v)} step={1} small /></Field>
      </Section>

      <Section title="TP/SL por Símbolo" defaultOpen={false}>
        <SymbolTPSLEditor data={rt.symbol_tp_sl || {}} onChange={v => set('runtime', { ...rt, symbol_tp_sl: v })} />
      </Section>

      <Section title="Risco por Símbolo" defaultOpen={false}>
        {Object.entries(rt.risk_by_symbol || {}).map(([sym, cfg]) => (
          <div key={sym} className="border border-border/50 rounded px-2 py-1 mb-1">
            <div className="text-xs font-bold text-primary mb-1">{sym}</div>
            <Field label="allow_new_orders"><Toggle value={cfg.allow_new_orders} onChange={v => updRBS(sym, 'allow_new_orders', v)} /></Field>
            <Field label="max_positions"><NumInput value={cfg.max_positions} onChange={v => updRBS(sym, 'max_positions', v)} step={1} small /></Field>
            <Field label="trailing_activation_points"><NumInput value={cfg.trailing_activation_points} onChange={v => updRBS(sym, 'trailing_activation_points', v)} step={1} small /></Field>
            <Field label="trailing_distance_points"><NumInput value={cfg.trailing_distance_points} onChange={v => updRBS(sym, 'trailing_distance_points', v)} step={1} small /></Field>
          </div>
        ))}
      </Section>
    </div>
  );
}
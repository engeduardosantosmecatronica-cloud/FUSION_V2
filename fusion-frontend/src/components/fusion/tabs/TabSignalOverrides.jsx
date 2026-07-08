import { useState } from 'react';
import { Field, Toggle, Section } from '../FusionFieldRenderers';
import { cn } from '@/lib/utils';

const ACTIONS = ['force_wait', 'block_buy', 'block_sell', 'force_buy', 'force_sell', 'invert', 'reduce_confidence'];
const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'GBPJPY', 'AUDCAD', 'USDCAD', '*'];

const EMPTY_RULE = { symbol: 'EURUSD', timeframe: 'H1', action: 'force_wait', enabled: false, reason: '', valid_until: '2026-12-31T23:59:00' };

export default function TabSignalOverrides({ draft, set }) {
  const so = draft.signal_overrides || { enabled: false, rules: [] };
  const [editing, setEditing] = useState(null); // index
  const [form, setForm] = useState(EMPTY_RULE);

  const updSO = (k, v) => set('signal_overrides', { ...so, [k]: v });
  const updateRule = (i, k, v) => {
    const rules = [...(so.rules || [])];
    rules[i] = { ...rules[i], [k]: v };
    updSO('rules', rules);
  };
  const removeRule = (i) => { const r = [...(so.rules || [])]; r.splice(i, 1); updSO('rules', r); };
  const addRule = () => {
    updSO('rules', [...(so.rules || []), { ...form }]);
    setForm(EMPTY_RULE);
    setEditing(null);
  };

  return (
    <div className="space-y-2">
      <Section title="Signal Overrides">
        <Field label="enabled"><Toggle value={so.enabled} onChange={v => updSO('enabled', v)} /></Field>
      </Section>

      {/* Add rule */}
      <div className="border border-border rounded p-3 space-y-2">
        <div className="text-xs font-bold text-muted-foreground uppercase">Nova Regra</div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-muted-foreground">Símbolo</label>
            <select value={form.symbol} onChange={e => setForm(f => ({ ...f, symbol: e.target.value }))} className="w-full mt-1 bg-secondary border border-border rounded px-2 py-1 text-xs">
              {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Timeframe</label>
            <select value={form.timeframe} onChange={e => setForm(f => ({ ...f, timeframe: e.target.value }))} className="w-full mt-1 bg-secondary border border-border rounded px-2 py-1 text-xs">
              {TIMEFRAMES.map(tf => <option key={tf} value={tf}>{tf}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Ação</label>
            <select value={form.action} onChange={e => setForm(f => ({ ...f, action: e.target.value }))} className="w-full mt-1 bg-secondary border border-border rounded px-2 py-1 text-xs">
              {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Válido até</label>
            <input type="datetime-local" value={form.valid_until?.slice(0, 16)} onChange={e => setForm(f => ({ ...f, valid_until: e.target.value }))} className="w-full mt-1 bg-secondary border border-border rounded px-2 py-1 text-xs" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-muted-foreground">Motivo</label>
            <input value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} className="w-full mt-1 bg-secondary border border-border rounded px-2 py-1 text-xs" />
          </div>
        </div>
        <button onClick={addRule} className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded hover:bg-primary/90">+ Adicionar Regra</button>
      </div>

      {/* Rules table */}
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Ativo','Ativo','TF','Ação','Motivo','Válido até','Status',''].map((h, i) => (
                <th key={i} className="px-2 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(so.rules || []).map((rule, i) => (
              <tr key={i} className="border-b border-border hover:bg-accent">
                <td className="px-2 py-1.5">
                  <Toggle value={rule.enabled} onChange={v => updateRule(i, 'enabled', v)} small />
                </td>
                <td className="px-2 py-1.5 font-bold">{rule.symbol}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{rule.timeframe}</td>
                <td className={cn('px-2 py-1.5 font-mono', rule.action.includes('buy') ? 'text-green-400' : rule.action.includes('sell') ? 'text-red-400' : 'text-yellow-400')}>
                  {rule.action}
                </td>
                <td className="px-2 py-1.5 text-muted-foreground max-w-32 truncate">{rule.reason}</td>
                <td className="px-2 py-1.5 font-mono text-muted-foreground">{rule.valid_until?.slice(0, 10)}</td>
                <td className={cn('px-2 py-1.5 font-medium', rule.enabled ? 'text-green-400' : 'text-muted-foreground')}>
                  {rule.enabled ? 'ativo' : 'inativo'}
                </td>
                <td className="px-2 py-1.5">
                  <button onClick={() => removeRule(i)} className="text-xs text-red-400 hover:text-red-300">×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(so.rules || []).length === 0 && <div className="text-center text-muted-foreground py-6 text-xs">Nenhuma regra de override</div>}
      </div>
    </div>
  );
}
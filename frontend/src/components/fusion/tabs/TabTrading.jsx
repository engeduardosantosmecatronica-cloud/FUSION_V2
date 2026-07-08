import { Field, Toggle, NumInput, TextInput, ModeSelect, Section } from '../FusionFieldRenderers';

const EXECUTION_MODES = ['automatic', 'manual', 'disabled', 'monitor'];
const SCOPES = ['system', 'symbol', 'strategy'];
const DIRECTION_MODES = ['any_direction', 'by_direction'];

function sub(obj, key) { return obj?.[key] || {}; }

export default function TabTrading({ draft, set }) {
  const t = draft.trading || {};
  const upd = (k, v) => set('trading', { ...t, [k]: v });
  const updSub = (sub_key, k, v) => upd(sub_key, { ...t[sub_key], [k]: v });

  return (
    <div className="space-y-2">
      <Section title="Execução">
        <Field label="allow_new_orders">
          <Toggle value={t.allow_new_orders} onChange={v => upd('allow_new_orders', v)} />
        </Field>
        <Field label="execution_mode">
          <select value={t.execution_mode || 'automatic'} onChange={e => upd('execution_mode', e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {EXECUTION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
      </Section>

      <Section title="Manual Approval" defaultOpen={false}>
        <Field label="enabled"><Toggle value={t.manual_approval?.enabled} onChange={v => updSub('manual_approval', 'enabled', v)} /></Field>
        <Field label="request_file"><TextInput value={t.manual_approval?.request_file} onChange={v => updSub('manual_approval', 'request_file', v)} wide /></Field>
        <Field label="response_file"><TextInput value={t.manual_approval?.response_file} onChange={v => updSub('manual_approval', 'response_file', v)} wide /></Field>
        <Field label="timeout_seconds" unit="s"><NumInput value={t.manual_approval?.timeout_seconds} onChange={v => updSub('manual_approval', 'timeout_seconds', v)} step={1} unit="s" small /></Field>
      </Section>

      <Section title="Close on Opposite Signal" defaultOpen={false}>
        <Field label="enabled"><Toggle value={t.close_on_opposite_signal?.enabled} onChange={v => updSub('close_on_opposite_signal', 'enabled', v)} /></Field>
        <Field label="source"><TextInput value={t.close_on_opposite_signal?.source} onChange={v => updSub('close_on_opposite_signal', 'source', v)} /></Field>
        <Field label="min_loss_money"><NumInput value={t.close_on_opposite_signal?.min_loss_money} onChange={v => updSub('close_on_opposite_signal', 'min_loss_money', v)} small /></Field>
        <Field label="scope">
          <select value={t.close_on_opposite_signal?.scope || 'system'} onChange={e => updSub('close_on_opposite_signal', 'scope', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="reason_code"><TextInput value={t.close_on_opposite_signal?.reason_code} onChange={v => updSub('close_on_opposite_signal', 'reason_code', v)} /></Field>
      </Section>

      <Section title="Floating Loss Guard" defaultOpen={false}>
        <Field label="enabled"><Toggle value={t.floating_loss_guard?.enabled} onChange={v => updSub('floating_loss_guard', 'enabled', v)} /></Field>
        <Field label="max_loss_money"><NumInput value={t.floating_loss_guard?.max_loss_money} onChange={v => updSub('floating_loss_guard', 'max_loss_money', v)} step={1} small /></Field>
        <Field label="scope">
          <select value={t.floating_loss_guard?.scope || 'system'} onChange={e => updSub('floating_loss_guard', 'scope', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
      </Section>

      <Section title="Daily Loss Guard" defaultOpen={false}>
        <Field label="enabled"><Toggle value={t.daily_loss_guard?.enabled} onChange={v => updSub('daily_loss_guard', 'enabled', v)} /></Field>
        <Field label="max_loss_pct" unit="%"><NumInput value={t.daily_loss_guard?.max_loss_pct} onChange={v => updSub('daily_loss_guard', 'max_loss_pct', v)} step={0.1} unit="%" small /></Field>
        <Field label="max_loss_money"><NumInput value={t.daily_loss_guard?.max_loss_money} onChange={v => updSub('daily_loss_guard', 'max_loss_money', v)} step={1} small /></Field>
        <Field label="include_commission_swap"><Toggle value={t.daily_loss_guard?.include_commission_swap} onChange={v => updSub('daily_loss_guard', 'include_commission_swap', v)} /></Field>
      </Section>

      <Section title="Reentry Cooldown" defaultOpen={false}>
        <Field label="enabled"><Toggle value={t.reentry_cooldown_after_close?.enabled} onChange={v => updSub('reentry_cooldown_after_close', 'enabled', v)} /></Field>
        <Field label="seconds" unit="s"><NumInput value={t.reentry_cooldown_after_close?.seconds} onChange={v => updSub('reentry_cooldown_after_close', 'seconds', v)} step={1} unit="s" small /></Field>
        <Field label="scope">
          <select value={t.reentry_cooldown_after_close?.scope || 'symbol'} onChange={e => updSub('reentry_cooldown_after_close', 'scope', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {SCOPES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
      </Section>

      <Section title="Position Limits" defaultOpen={false}>
        <Field label="enabled"><Toggle value={t.position_limits?.enabled} onChange={v => updSub('position_limits', 'enabled', v)} /></Field>
        <Field label="scope">
          <select value={t.position_limits?.scope || 'system'} onChange={e => updSub('position_limits', 'scope', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {['system', 'strategy'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="max_per_symbol"><NumInput value={t.position_limits?.max_per_symbol} onChange={v => updSub('position_limits', 'max_per_symbol', v)} step={1} small /></Field>
        <Field label="mode">
          <select value={t.position_limits?.mode || 'any_direction'} onChange={e => updSub('position_limits', 'mode', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {DIRECTION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
      </Section>
    </div>
  );
}
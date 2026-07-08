import { Field, Toggle, NumInput, TextInput, ChipListEditor, Section } from '../FusionFieldRenderers';

const MODES = ['apply', 'block', 'shadow', 'off'];
const STARTUP_MODES = ['background', 'blocking'];

export default function TabOTM({ draft, set }) {
  const otm = draft.operational_target_matrix || {};
  const upd = (k, v) => set('operational_target_matrix', { ...otm, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="Operational Target Matrix">
        <Field label="enabled"><Toggle value={otm.enabled} onChange={v => upd('enabled', v)} /></Field>
        <Field label="mode">
          <select value={otm.mode || 'apply'} onChange={e => upd('mode', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {MODES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
        <Field label="update_on_startup"><Toggle value={otm.update_on_startup} onChange={v => upd('update_on_startup', v)} /></Field>
        <Field label="startup_mode">
          <select value={otm.startup_mode || 'background'} onChange={e => upd('startup_mode', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {STARTUP_MODES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>
        <Field label="output_dir"><TextInput value={otm.output_dir} onChange={v => upd('output_dir', v)} wide /></Field>
        <Field label="lookback_days" unit="d"><NumInput value={otm.lookback_days} onChange={v => upd('lookback_days', v)} step={1} unit="d" small /></Field>
        <Field label="lookahead_minutes" unit="min"><NumInput value={otm.lookahead_minutes} onChange={v => upd('lookahead_minutes', v)} step={1} unit="min" small /></Field>
        <Field label="decision_filter"><TextInput value={otm.decision_filter} onChange={v => upd('decision_filter', v)} /></Field>
        <Field label="market_time_offset_hours" unit="h"><NumInput value={otm.market_time_offset_hours} onChange={v => upd('market_time_offset_hours', v)} step={1} unit="h" small /></Field>
        <Field label="min_samples"><NumInput value={otm.min_samples} onChange={v => upd('min_samples', v)} step={1} small /></Field>
        <Field label="max_startup_seconds" unit="s"><NumInput value={otm.max_startup_seconds} onChange={v => upd('max_startup_seconds', v)} step={1} unit="s" small /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">targets</div><ChipListEditor value={(otm.targets || []).map(String)} onChange={v => upd('targets', v.map(Number))} /></div>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">stops</div><ChipListEditor value={(otm.stops || []).map(String)} onChange={v => upd('stops', v.map(Number))} /></div>
        <Field label="max_loss_streak"><NumInput value={otm.max_loss_streak} onChange={v => upd('max_loss_streak', v)} step={1} small /></Field>
        <Field label="min_win_rate"><NumInput value={otm.min_win_rate} onChange={v => upd('min_win_rate', v)} step={0.01} small /></Field>
        <Field label="use_mt5"><Toggle value={otm.use_mt5} onChange={v => upd('use_mt5', v)} /></Field>
        <Field label="save_mt5_history"><Toggle value={otm.save_mt5_history} onChange={v => upd('save_mt5_history', v)} /></Field>
        <Field label="latest_path"><TextInput value={otm.latest_path} onChange={v => upd('latest_path', v)} wide /></Field>
      </Section>
    </div>
  );
}
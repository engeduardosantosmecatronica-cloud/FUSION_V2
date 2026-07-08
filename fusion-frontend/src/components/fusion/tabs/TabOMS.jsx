import { Field, Toggle, NumInput, TextInput, Section } from '../FusionFieldRenderers';

export default function TabOMS({ draft, set }) {
  const oms = draft.oms || {};
  const upd = (k, v) => set('oms', { ...oms, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="OMS (Order Management System)">
        <Field label="snapshot_enabled"><Toggle value={oms.snapshot_enabled} onChange={v => upd('snapshot_enabled', v)} /></Field>
        <Field label="snapshot_dir"><TextInput value={oms.snapshot_dir} onChange={v => upd('snapshot_dir', v)} wide /></Field>
        <Field label="trade_history_lookback_hours" unit="h">
          <NumInput value={oms.trade_history_lookback_hours} onChange={v => upd('trade_history_lookback_hours', v)} step={1} unit="h" small />
        </Field>
      </Section>
    </div>
  );
}
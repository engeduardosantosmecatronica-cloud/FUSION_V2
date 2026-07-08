import { Field, Toggle, NumInput, TextInput, ChipListEditor, Section } from '../FusionFieldRenderers';

export default function TabModelos({ draft, set }) {
  const m = draft.model || {};
  const ae = draft.approved_ensembles || {};
  const ara = draft.ai_review_agent || {};
  const ab = draft.ai_bridge || {};
  const updM = (k, v) => set('model', { ...m, [k]: v });
  const updAE = (k, v) => set('approved_ensembles', { ...ae, [k]: v });
  const updARA = (k, v) => set('ai_review_agent', { ...ara, [k]: v });
  const updAB = (k, v) => set('ai_bridge', { ...ab, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="Model">
        <Field label="model_dir"><TextInput value={m.model_dir} onChange={v => updM('model_dir', v)} wide /></Field>
        <Field label="global_model"><TextInput value={m.global_model} onChange={v => updM('global_model', v)} /></Field>
        <Field label="scaler"><TextInput value={m.scaler} onChange={v => updM('scaler', v)} /></Field>
        <Field label="meta"><TextInput value={m.meta} onChange={v => updM('meta', v)} /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">feature_columns</div><ChipListEditor value={m.feature_columns || []} onChange={v => updM('feature_columns', v)} /></div>
      </Section>

      <Section title="Approved Ensembles" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ae.enabled} onChange={v => updAE('enabled', v)} /></Field>
        <Field label="registry_path"><TextInput value={ae.registry_path} onChange={v => updAE('registry_path', v)} wide /></Field>
        <Field label="tp_sl_report"><TextInput value={ae.tp_sl_report} onChange={v => updAE('tp_sl_report', v)} wide /></Field>
        <Field label="min_member_weight"><NumInput value={ae.min_member_weight} onChange={v => updAE('min_member_weight', v)} step={0.01} small /></Field>
        <Field label="min_score"><NumInput value={ae.min_score} onChange={v => updAE('min_score', v)} step={0.01} small /></Field>
        <Field label="bars"><NumInput value={ae.bars} onChange={v => updAE('bars', v)} step={1} small /></Field>
      </Section>

      <Section title="AI Review Agent" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ara.enabled} onChange={v => updARA('enabled', v)} /></Field>
        <Field label="endpoint_url"><TextInput value={ara.endpoint_url} onChange={v => updARA('endpoint_url', v)} wide /></Field>
        <Field label="timeout_seconds" unit="s"><NumInput value={ara.timeout_seconds} onChange={v => updARA('timeout_seconds', v)} step={1} unit="s" small /></Field>
        <Field label="fail_open"><Toggle value={ara.fail_open} onChange={v => updARA('fail_open', v)} /></Field>
        <Field label="model_hint"><TextInput value={ara.model_hint} onChange={v => updARA('model_hint', v)} /></Field>
        <Field label="max_events"><NumInput value={ara.max_events} onChange={v => updARA('max_events', v)} step={1} small /></Field>
        <Field label="auto_apply_changes"><Toggle value={ara.auto_apply_changes} onChange={v => updARA('auto_apply_changes', v)} /></Field>
      </Section>

      <Section title="AI Bridge" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ab.enabled} onChange={v => updAB('enabled', v)} /></Field>
        <Field label="host"><TextInput value={ab.host} onChange={v => updAB('host', v)} /></Field>
        <Field label="port"><NumInput value={ab.port} onChange={v => updAB('port', v)} step={1} /></Field>
        <Field label="provider"><TextInput value={ab.provider} onChange={v => updAB('provider', v)} /></Field>
        <Field label="model_hint"><TextInput value={ab.model_hint} onChange={v => updAB('model_hint', v)} /></Field>
      </Section>
    </div>
  );
}
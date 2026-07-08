import { Field, Toggle, NumInput, TextInput, ModeSelect, ChipListEditor, Section } from '../FusionFieldRenderers';

function TFWeights({ weights, onChange }) {
  return (
    <div className="grid grid-cols-3 gap-1">
      {['M5','M15','M30','H1','H4','D1'].map(tf => (
        <div key={tf} className="flex items-center gap-1">
          <span className="text-xs text-muted-foreground w-6">{tf}</span>
          <input type="number" step="0.1" min="0" max="3" value={weights?.[tf] ?? 1}
            onChange={e => onChange({ ...weights, [tf]: parseFloat(e.target.value) })}
            className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-14 font-mono text-right" />
        </div>
      ))}
    </div>
  );
}

export default function TabCurrencyStrength({ draft, set }) {
  const cs = draft.currency_strength_map || {};
  const fnd = cs.false_neutral_detector || {};
  const dsg = cs.directional_signal_guard || {};
  const upd = (k, v) => set('currency_strength_map', { ...cs, [k]: v });
  const updFND = (k, v) => upd('false_neutral_detector', { ...fnd, [k]: v });
  const updDSG = (k, v) => upd('directional_signal_guard', { ...dsg, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="Currency Strength Map">
        <Field label="enabled"><Toggle value={cs.enabled} onChange={v => upd('enabled', v)} /></Field>
        <Field label="output_dir"><TextInput value={cs.output_dir} onChange={v => upd('output_dir', v)} wide /></Field>
        <Field label="write_csv"><Toggle value={cs.write_csv} onChange={v => upd('write_csv', v)} /></Field>
        <Field label="write_json"><Toggle value={cs.write_json} onChange={v => upd('write_json', v)} /></Field>
        <Field label="wait_edge"><NumInput value={cs.wait_edge} onChange={v => upd('wait_edge', v)} step={0.01} small /></Field>
        <Field label="min_confidence_weight"><NumInput value={cs.min_confidence_weight} onChange={v => upd('min_confidence_weight', v)} step={0.01} small /></Field>
        <Field label="moderate_pair_score"><NumInput value={cs.moderate_pair_score} onChange={v => upd('moderate_pair_score', v)} step={0.01} small /></Field>
        <Field label="strong_pair_score"><NumInput value={cs.strong_pair_score} onChange={v => upd('strong_pair_score', v)} step={0.01} small /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">timeframe_weights</div><TFWeights weights={cs.timeframe_weights} onChange={v => upd('timeframe_weights', v)} /></div>
      </Section>

      <Section title="False Neutral Detector" defaultOpen={false}>
        <Field label="enabled"><Toggle value={fnd.enabled} onChange={v => updFND('enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={fnd.mode} onChange={v => updFND('mode', v)} /></Field>
        <Field label="write_csv"><Toggle value={fnd.write_csv} onChange={v => updFND('write_csv', v)} /></Field>
        <Field label="min_pair_score"><NumInput value={fnd.min_pair_score} onChange={v => updFND('min_pair_score', v)} step={0.01} small /></Field>
        <Field label="min_aligned_timeframes"><NumInput value={fnd.min_aligned_timeframes} onChange={v => updFND('min_aligned_timeframes', v)} step={1} small /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">structural_timeframes</div><ChipListEditor value={fnd.structural_timeframes || []} onChange={v => updFND('structural_timeframes', v)} /></div>
        <Field label="require_structural_for_short_tf"><Toggle value={fnd.require_structural_for_short_tf} onChange={v => updFND('require_structural_for_short_tf', v)} /></Field>
      </Section>

      <Section title="Directional Signal Guard" defaultOpen={false}>
        <Field label="enabled"><Toggle value={dsg.enabled} onChange={v => updDSG('enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={dsg.mode} onChange={v => updDSG('mode', v)} /></Field>
        <Field label="write_csv"><Toggle value={dsg.write_csv} onChange={v => updDSG('write_csv', v)} /></Field>
        <Field label="min_confirm_score"><NumInput value={dsg.min_confirm_score} onChange={v => updDSG('min_confirm_score', v)} step={0.01} small /></Field>
        <Field label="min_conflict_score"><NumInput value={dsg.min_conflict_score} onChange={v => updDSG('min_conflict_score', v)} step={0.01} small /></Field>
        <Field label="reason_code"><TextInput value={dsg.reason_code} onChange={v => updDSG('reason_code', v)} /></Field>
      </Section>
    </div>
  );
}
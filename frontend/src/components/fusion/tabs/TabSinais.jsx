import { Field, Toggle, NumInput, ChipListEditor, Section } from '../FusionFieldRenderers';

export default function TabSinais({ draft, set }) {
  const s = draft.signal || {};
  const rs = draft.runtime?.signals || {};
  const updS = (k, v) => set('signal', { ...s, [k]: v });
  const updRS = (k, v) => set('runtime', { ...draft.runtime, signals: { ...rs, [k]: v } });

  return (
    <div className="space-y-2">
      <Section title="Sinais (config)">
        <Field label="buy_threshold"><NumInput value={s.buy_threshold} onChange={v => updS('buy_threshold', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="sell_threshold"><NumInput value={s.sell_threshold} onChange={v => updS('sell_threshold', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="confidence_filter"><NumInput value={s.confidence_filter} onChange={v => updS('confidence_filter', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="min_signal_strength"><NumInput value={s.min_signal_strength} onChange={v => updS('min_signal_strength', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="invert_signals"><Toggle value={s.invert_signals} onChange={v => updS('invert_signals', v)} /></Field>
        <div className="py-1.5">
          <div className="text-xs text-muted-foreground mb-1">inverted_signal_groups</div>
          <ChipListEditor value={s.inverted_signal_groups || []} onChange={v => updS('inverted_signal_groups', v)} />
        </div>
      </Section>

      <Section title="Runtime Signals (hotload)">
        <Field label="buy_threshold"><NumInput value={rs.buy_threshold} onChange={v => updRS('buy_threshold', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="sell_threshold"><NumInput value={rs.sell_threshold} onChange={v => updRS('sell_threshold', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="confidence_filter"><NumInput value={rs.confidence_filter} onChange={v => updRS('confidence_filter', v)} step={0.01} min={0} max={1} small /></Field>
        <Field label="min_signal_strength"><NumInput value={rs.min_signal_strength} onChange={v => updRS('min_signal_strength', v)} step={0.01} min={0} max={1} small /></Field>
      </Section>
    </div>
  );
}
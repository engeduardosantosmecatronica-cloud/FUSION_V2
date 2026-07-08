import { Field, Toggle, NumInput, Section } from '../FusionFieldRenderers';

export default function TabRisco({ draft, set }) {
  const r = draft.risk || {};
  const rt = draft.runtime?.trading || {};
  const updR = (k, v) => set('risk', { ...r, [k]: v });
  const updRT = (k, v) => set('runtime', { ...draft.runtime, trading: { ...rt, [k]: v } });

  return (
    <div className="space-y-2">
      <Section title="Risco Global">
        <Field label="max_risk_per_trade" unit="%"><NumInput value={r.max_risk_per_trade} onChange={v => updR('max_risk_per_trade', v)} step={0.1} unit="%" small /></Field>
        <Field label="max_daily_loss" unit="%"><NumInput value={r.max_daily_loss} onChange={v => updR('max_daily_loss', v)} step={0.1} unit="%" small /></Field>
        <Field label="max_positions"><NumInput value={r.max_positions} onChange={v => updR('max_positions', v)} step={1} small /></Field>
        <Field label="lot_step"><NumInput value={r.lot_step} onChange={v => updR('lot_step', v)} step={0.01} small /></Field>
        <Field label="min_lot"><NumInput value={r.min_lot} onChange={v => updR('min_lot', v)} step={0.01} small /></Field>
        <Field label="max_lot"><NumInput value={r.max_lot} onChange={v => updR('max_lot', v)} step={0.1} small /></Field>
        <Field label="default_sl_points"><NumInput value={r.default_sl_points} onChange={v => updR('default_sl_points', v)} step={1} small /></Field>
      </Section>

      <Section title="Runtime Trading (hotload)">
        <Field label="max_positions"><NumInput value={rt.max_positions} onChange={v => updRT('max_positions', v)} step={1} small /></Field>
        <Field label="max_positions_per_symbol"><NumInput value={rt.max_positions_per_symbol} onChange={v => updRT('max_positions_per_symbol', v)} step={1} small /></Field>
        <Field label="max_daily_loss_money"><NumInput value={rt.max_daily_loss_money} onChange={v => updRT('max_daily_loss_money', v)} step={1} small /></Field>
        <Field label="max_floating_loss_money"><NumInput value={rt.max_floating_loss_money} onChange={v => updRT('max_floating_loss_money', v)} step={1} small /></Field>
      </Section>
    </div>
  );
}
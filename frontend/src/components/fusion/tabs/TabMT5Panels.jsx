import { Field, Toggle, NumInput, TextInput, Section } from '../FusionFieldRenderers';

export default function TabMT5Panels({ draft, set }) {
  const sp = draft.mt5_signal_panel || {};
  const rd = sp.refined_display || {};
  const tz = draft.mt5_trade_zones || {};
  const dl = draft.mt5_decision_layers || {};

  const updSP = (k, v) => set('mt5_signal_panel', { ...sp, [k]: v });
  const updRD = (k, v) => updSP('refined_display', { ...rd, [k]: v });
  const updTZ = (k, v) => set('mt5_trade_zones', { ...tz, [k]: v });
  const updDL = (k, v) => set('mt5_decision_layers', { ...dl, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="MT5 Signal Panel">
        <Field label="enabled"><Toggle value={sp.enabled} onChange={v => updSP('enabled', v)} /></Field>
        <Field label="use_common_files"><Toggle value={sp.use_common_files} onChange={v => updSP('use_common_files', v)} /></Field>
        <Field label="output_dir"><TextInput value={sp.output_dir ?? ''} onChange={v => updSP('output_dir', v || null)} /></Field>
        <Field label="file_prefix"><TextInput value={sp.file_prefix} onChange={v => updSP('file_prefix', v)} /></Field>
      </Section>

      <Section title="Refined Display" defaultOpen={false}>
        {['enabled','show_final_row','require_operational_matrix','require_recommended','block_on_missing_matrix','block_on_low_samples','block_on_missing_target_plan','keep_raw_reason'].map(k => (
          <Field key={k} label={k}><Toggle value={rd[k]} onChange={v => updRD(k, v)} /></Field>
        ))}
        <Field label="matrix_path"><TextInput value={rd.matrix_path} onChange={v => updRD('matrix_path', v)} wide /></Field>
        <Field label="min_samples"><NumInput value={rd.min_samples} onChange={v => updRD('min_samples', v)} step={1} small /></Field>
      </Section>

      <Section title="MT5 Trade Zones" defaultOpen={false}>
        <Field label="enabled"><Toggle value={tz.enabled} onChange={v => updTZ('enabled', v)} /></Field>
        <Field label="use_common_files"><Toggle value={tz.use_common_files} onChange={v => updTZ('use_common_files', v)} /></Field>
        <Field label="output_dir"><TextInput value={tz.output_dir ?? ''} onChange={v => updTZ('output_dir', v || null)} /></Field>
        <Field label="file_prefix"><TextInput value={tz.file_prefix} onChange={v => updTZ('file_prefix', v)} /></Field>
        <Field label="bars"><NumInput value={tz.bars} onChange={v => updTZ('bars', v)} step={1} small /></Field>
        <Field label="sr_lookback"><NumInput value={tz.sr_lookback} onChange={v => updTZ('sr_lookback', v)} step={1} small /></Field>
        <Field label="atr_period"><NumInput value={tz.atr_period} onChange={v => updTZ('atr_period', v)} step={1} small /></Field>
        <Field label="entry_atr_width"><NumInput value={tz.entry_atr_width} onChange={v => updTZ('entry_atr_width', v)} step={0.1} small /></Field>
        <Field label="sr_atr_width"><NumInput value={tz.sr_atr_width} onChange={v => updTZ('sr_atr_width', v)} step={0.1} small /></Field>
        <Field label="sl_atr_multiplier"><NumInput value={tz.sl_atr_multiplier} onChange={v => updTZ('sl_atr_multiplier', v)} step={0.1} small /></Field>
        <Field label="tp_r_multiple"><NumInput value={tz.tp_r_multiple} onChange={v => updTZ('tp_r_multiple', v)} step={0.1} small /></Field>
      </Section>

      <Section title="MT5 Decision Layers" defaultOpen={false}>
        <Field label="enabled"><Toggle value={dl.enabled} onChange={v => updDL('enabled', v)} /></Field>
        <Field label="use_common_files"><Toggle value={dl.use_common_files} onChange={v => updDL('use_common_files', v)} /></Field>
        <Field label="output_dir"><TextInput value={dl.output_dir ?? ''} onChange={v => updDL('output_dir', v || null)} /></Field>
        <Field label="file_prefix"><TextInput value={dl.file_prefix} onChange={v => updDL('file_prefix', v)} /></Field>
      </Section>
    </div>
  );
}
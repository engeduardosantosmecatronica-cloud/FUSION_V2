import { Field, Toggle, NumInput, TextInput, ChipListEditor, Section } from '../FusionFieldRenderers';

const COMMON_FIELDS = ['enabled', 'invert_signal', 'magic_base', 'max_positions_per_symbol', 'max_positions_per_side', 'cooldown_seconds'];
const DIRECTION_MODES = ['any_direction', 'by_direction'];
const SCOPES = ['strategy', 'system'];

function StrategyCommon({ s, upd }) {
  return (
    <>
      {['enabled', 'invert_signal'].map(k => (
        <Field key={k} label={k}><Toggle value={s[k]} onChange={v => upd(k, v)} /></Field>
      ))}
      <Field label="magic_base"><NumInput value={s.magic_base} onChange={v => upd('magic_base', v)} step={1} /></Field>
      <div className="py-1"><div className="text-xs text-muted-foreground mb-1">legacy_magics</div><ChipListEditor value={s.legacy_magics || []} onChange={v => upd('legacy_magics', v)} /></div>
      {['max_positions_per_symbol', 'max_positions_per_side', 'cooldown_seconds'].map(k => (
        <Field key={k} label={k}><NumInput value={s[k]} onChange={v => upd(k, v)} step={1} small /></Field>
      ))}
      <Field label="max_positions_mode">
        <select value={s.max_positions_mode || 'any_direction'} onChange={e => upd('max_positions_mode', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
          {DIRECTION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </Field>
      <Field label="max_positions_scope">
        <select value={s.max_positions_scope || 'strategy'} onChange={e => upd('max_positions_scope', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
          {SCOPES.map(sc => <option key={sc} value={sc}>{sc}</option>)}
        </select>
      </Field>
    </>
  );
}

function FeatureFields({ s, upd }) {
  return (
    <>
      <Field label="features_path"><TextInput value={s.features_path} onChange={v => upd('features_path', v)} wide /></Field>
      <Field label="min_entries"><NumInput value={s.min_entries} onChange={v => upd('min_entries', v)} step={1} small /></Field>
      <Field label="min_win_rate"><NumInput value={s.min_win_rate} onChange={v => upd('min_win_rate', v)} step={0.01} small /></Field>
      <Field label="min_score"><NumInput value={s.min_score} onChange={v => upd('min_score', v)} step={0.01} small /></Field>
      <Field label="target_preference"><NumInput value={s.target_preference} onChange={v => upd('target_preference', v)} step={1} small /></Field>
      <Field label="use_feature_tp_sl"><Toggle value={s.use_feature_tp_sl} onChange={v => upd('use_feature_tp_sl', v)} /></Field>
      <Field label="use_feature_sl"><Toggle value={s.use_feature_sl} onChange={v => upd('use_feature_sl', v)} /></Field>
      <Field label="default_tp_points"><NumInput value={s.default_tp_points} onChange={v => upd('default_tp_points', v)} step={1} small /></Field>
      <Field label="default_sl_points"><NumInput value={s.default_sl_points} onChange={v => upd('default_sl_points', v)} step={1} small /></Field>
    </>
  );
}

export default function TabStrategies({ draft, set }) {
  const strats = draft.strategies || {};
  const upd = (name, k, v) => set('strategies', { ...strats, [name]: { ...strats[name], [k]: v } });

  return (
    <div className="space-y-2">
      {/* Strategy 1 */}
      <Section title="strategy1 — Tendência Simples">
        <StrategyCommon s={strats.strategy1 || {}} upd={(k, v) => upd('strategy1', k, v)} />
        <Field label="use_tp_sl"><Toggle value={strats.strategy1?.use_tp_sl} onChange={v => upd('strategy1', 'use_tp_sl', v)} /></Field>
        <Field label="tp_points"><NumInput value={strats.strategy1?.tp_points} onChange={v => upd('strategy1', 'tp_points', v)} step={1} small /></Field>
        <Field label="sl_points"><NumInput value={strats.strategy1?.sl_points} onChange={v => upd('strategy1', 'sl_points', v)} step={1} small /></Field>
      </Section>

      {/* Strategy 2 */}
      <Section title="strategy2 — Ensemble Features" defaultOpen={false}>
        <StrategyCommon s={strats.strategy2 || {}} upd={(k, v) => upd('strategy2', k, v)} />
        <FeatureFields s={strats.strategy2 || {}} upd={(k, v) => upd('strategy2', k, v)} />
      </Section>

      {/* Strategy 3 */}
      <Section title="strategy3 — Ensemble + Exposição" defaultOpen={false}>
        <StrategyCommon s={strats.strategy3 || {}} upd={(k, v) => upd('strategy3', k, v)} />
        <FeatureFields s={strats.strategy3 || {}} upd={(k, v) => upd('strategy3', k, v)} />
        <Field label="use_exposure_groups"><Toggle value={strats.strategy3?.use_exposure_groups} onChange={v => upd('strategy3', 'use_exposure_groups', v)} /></Field>
      </Section>

      {/* Strategy 4 */}
      <Section title="strategy4 — Setup Manual" defaultOpen={false}>
        <StrategyCommon s={strats.strategy4 || {}} upd={(k, v) => upd('strategy4', k, v)} />
        <Field label="log_setup_details"><Toggle value={strats.strategy4?.log_setup_details} onChange={v => upd('strategy4', 'log_setup_details', v)} /></Field>
        <Field label="symbol"><TextInput value={strats.strategy4?.symbol} onChange={v => upd('strategy4', 'symbol', v)} /></Field>
        <Field label="broker_symbol"><TextInput value={strats.strategy4?.broker_symbol} onChange={v => upd('strategy4', 'broker_symbol', v)} /></Field>
        <Field label="only_buy"><Toggle value={strats.strategy4?.only_buy} onChange={v => upd('strategy4', 'only_buy', v)} /></Field>
        <Field label="setup"><TextInput value={strats.strategy4?.setup} onChange={v => upd('strategy4', 'setup', v)} /></Field>
        <Field label="rule"><TextInput value={strats.strategy4?.rule} onChange={v => upd('strategy4', 'rule', v)} /></Field>
        <Field label="ema_alignment.enabled"><Toggle value={strats.strategy4?.ema_alignment?.enabled} onChange={v => upd('strategy4', 'ema_alignment', { ...strats.strategy4?.ema_alignment, enabled: v })} /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">ema_alignment.periods</div><ChipListEditor value={(strats.strategy4?.ema_alignment?.periods || []).map(String)} onChange={v => upd('strategy4', 'ema_alignment', { ...strats.strategy4?.ema_alignment, periods: v.map(Number) })} /></div>
        <Field label="use_tp_sl"><Toggle value={strats.strategy4?.use_tp_sl} onChange={v => upd('strategy4', 'use_tp_sl', v)} /></Field>
        <Field label="sl_points"><NumInput value={strats.strategy4?.sl_points} onChange={v => upd('strategy4', 'sl_points', v)} step={1} small /></Field>
      </Section>

      {/* Strategy 5 */}
      <Section title="strategy5 — Feature SL/TP" defaultOpen={false}>
        <StrategyCommon s={strats.strategy5 || {}} upd={(k, v) => upd('strategy5', k, v)} />
        <Field label="use_feature_tp_sl"><Toggle value={strats.strategy5?.use_feature_tp_sl} onChange={v => upd('strategy5', 'use_feature_tp_sl', v)} /></Field>
        <Field label="use_feature_sl"><Toggle value={strats.strategy5?.use_feature_sl} onChange={v => upd('strategy5', 'use_feature_sl', v)} /></Field>
        <Field label="default_tp_points"><NumInput value={strats.strategy5?.default_tp_points} onChange={v => upd('strategy5', 'default_tp_points', v)} step={1} small /></Field>
        <Field label="default_sl_points"><NumInput value={strats.strategy5?.default_sl_points} onChange={v => upd('strategy5', 'default_sl_points', v)} step={1} small /></Field>
      </Section>

      {/* Strategy 6 */}
      <Section title="strategy6 — Multi-Expert" defaultOpen={false}>
        <StrategyCommon s={strats.strategy6 || {}} upd={(k, v) => upd('strategy6', k, v)} />
        <FeatureFields s={strats.strategy6 || {}} upd={(k, v) => upd('strategy6', k, v)} />
        {['enabled_experts', 'enabled_features', 'enabled_omnis_features'].map(k => (
          <div key={k} className="py-1"><div className="text-xs text-muted-foreground mb-1">{k}</div><ChipListEditor value={strats.strategy6?.[k] || []} onChange={v => upd('strategy6', k, v)} /></div>
        ))}
        {['require_expert_confirmation','require_feature_rule','log_each_loop'].map(k => (
          <Field key={k} label={k}><Toggle value={strats.strategy6?.[k]} onChange={v => upd('strategy6', k, v)} /></Field>
        ))}
        {['expert_min_confidence','expert_min_score'].map(k => (
          <Field key={k} label={k}><NumInput value={strats.strategy6?.[k]} onChange={v => upd('strategy6', k, v)} step={0.01} small /></Field>
        ))}
        {['min_expert_votes','bars'].map(k => (
          <Field key={k} label={k}><NumInput value={strats.strategy6?.[k]} onChange={v => upd('strategy6', k, v)} step={1} small /></Field>
        ))}
        <Field label="log_dir"><TextInput value={strats.strategy6?.log_dir} onChange={v => upd('strategy6', 'log_dir', v)} wide /></Field>
        <Field label="tp_points"><NumInput value={strats.strategy6?.tp_points} onChange={v => upd('strategy6', 'tp_points', v)} step={1} small /></Field>
        <Field label="sl_points"><NumInput value={strats.strategy6?.sl_points} onChange={v => upd('strategy6', 'sl_points', v)} step={1} small /></Field>
      </Section>
    </div>
  );
}
import { Field, Toggle, NumInput, ModeSelect, ChipListEditor, Section } from '../FusionFieldRenderers';
import { cn } from '@/lib/utils';

const FILTER_MODES = ['block', 'shadow', 'off'];

const RUNTIME_FILTER_KEYS = [
  'portfolio_exposure_mode', 'portfolio_correlation_mode', 'market_briefing_mode',
  'market_regime_mode', 'volatility_engine_mode', 'session_context_mode',
  'macro_flow_mode', 'market_structure_mode', 'opportunity_engine_mode',
  'execution_engine_mode', 'entry_timing_mode', 'risk_engine_mode',
  'ema_alignment_mode', 'context_engine_mode', 'context_brain_mode',
  'ema_lower_timeframes_direction_mode', 'candle_price_confirmation_mode',
  'market_alignment_mode', 'timeframe_consensus_mode',
];

function FilterRuntimeRow({ name, value, onChange }) {
  const MODE_COLORS = { block: 'text-red-400', shadow: 'text-yellow-400', off: 'text-muted-foreground' };
  return (
    <div className="flex items-center justify-between gap-2 py-1 border-b border-border/50">
      <span className="text-xs font-mono text-muted-foreground truncate">{name.replace('_mode', '')}</span>
      <select value={value || 'off'} onChange={e => onChange(e.target.value)}
        className={cn('bg-secondary border border-border rounded px-2 py-0.5 text-xs', MODE_COLORS[value] || '')}>
        {FILTER_MODES.map(m => <option key={m} value={m} className="text-foreground bg-popover">{m}</option>)}
      </select>
    </div>
  );
}

function TFWeightsEditor({ weights, onChange }) {
  const TFS = ['M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
  return (
    <div className="grid grid-cols-3 gap-1">
      {TFS.map(tf => (
        <div key={tf} className="flex items-center gap-1">
          <span className="text-xs text-muted-foreground w-6">{tf}</span>
          <input type="number" step="0.1" min="0" max="3" value={weights?.[tf] ?? 1}
            onChange={e => onChange({ ...weights, [tf]: parseFloat(e.target.value) })}
            className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-12 text-right font-mono" />
        </div>
      ))}
    </div>
  );
}

export default function TabFiltros({ draft, set }) {
  const rf = draft.runtime?.filters || {};
  const ef = draft.entry_filters || {};
  const updRF = (k, v) => set('runtime', { ...draft.runtime, filters: { ...rf, [k]: v } });
  const updEF = (filter, k, v) => set('entry_filters', { ...ef, [filter]: { ...ef[filter], [k]: v } });
  const updEFSub = (filter, sub, k, v) => updEF(filter, sub, { ...(ef[filter]?.[sub] || {}), [k]: v });

  return (
    <div className="space-y-2">
      {/* Runtime filter modes */}
      <Section title="Modos Runtime (hotload)">
        <Field label="block_top_bottom_without_breakout">
          <Toggle value={rf.block_top_bottom_without_breakout} onChange={v => updRF('block_top_bottom_without_breakout', v)} />
        </Field>
        <div className="grid grid-cols-2 gap-x-6 mt-1">
          {RUNTIME_FILTER_KEYS.map(k => (
            <FilterRuntimeRow key={k} name={k} value={rf[k]} onChange={v => updRF(k, v)} />
          ))}
        </div>
        <div className="mt-2">
          <div className="text-xs text-muted-foreground mb-1">market_alignment_block_states</div>
          <ChipListEditor value={rf.market_alignment_block_states || []} onChange={v => updRF('market_alignment_block_states', v)} />
        </div>
        <div className="mt-2">
          <div className="text-xs text-muted-foreground mb-1">timeframe_consensus_block_states</div>
          <ChipListEditor value={rf.timeframe_consensus_block_states || []} onChange={v => updRF('timeframe_consensus_block_states', v)} />
        </div>
      </Section>

      {/* Entry filters */}
      <Section title="market_alignment" defaultOpen={false}>
        {['enabled', 'mode', 'reason_code', 'log_each_check', 'write_monitor_log', 'require_h1_or_h4_alignment', 'block_lower_tf_against_h4_d1'].map(k => (
          <Field key={k} label={k}>
            {k === 'mode' ? <ModeSelect value={ef.market_alignment?.[k]} onChange={v => updEF('market_alignment', k, v)} />
              : typeof (ef.market_alignment?.[k]) === 'boolean' ? <Toggle value={ef.market_alignment?.[k]} onChange={v => updEF('market_alignment', k, v)} />
              : <input type="text" value={ef.market_alignment?.[k] ?? ''} onChange={e => updEF('market_alignment', k, e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-40" />}
          </Field>
        ))}
        {['min_alignment_score', 'min_structural_score', 'chop_abs_score'].map(k => (
          <Field key={k} label={k}><input type="number" step="0.01" value={ef.market_alignment?.[k] ?? ''} onChange={e => updEF('market_alignment', k, parseFloat(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">block_states</div><ChipListEditor value={ef.market_alignment?.block_states || []} onChange={v => updEF('market_alignment', 'block_states', v)} /></div>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">timeframe_weights</div><TFWeightsEditor weights={ef.market_alignment?.timeframe_weights} onChange={v => updEF('market_alignment', 'timeframe_weights', v)} /></div>
      </Section>

      <Section title="timeframe_consensus" defaultOpen={false}>
        {['enabled', 'log_each_check', 'require_h1_or_h4_alignment', 'block_lower_tf_against_h4_d1'].map(k => (
          <Field key={k} label={k}><Toggle value={ef.timeframe_consensus?.[k]} onChange={v => updEF('timeframe_consensus', k, v)} /></Field>
        ))}
        <Field label="mode"><ModeSelect value={ef.timeframe_consensus?.mode} onChange={v => updEF('timeframe_consensus', 'mode', v)} /></Field>
        {['wait_edge', 'min_valid_timeframes', 'min_consensus_score', 'min_structural_score'].map(k => (
          <Field key={k} label={k}><input type="number" step="0.01" value={ef.timeframe_consensus?.[k] ?? ''} onChange={e => updEF('timeframe_consensus', k, parseFloat(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">block_states</div><ChipListEditor value={ef.timeframe_consensus?.block_states || []} onChange={v => updEF('timeframe_consensus', 'block_states', v)} /></div>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">timeframe_weights</div><TFWeightsEditor weights={ef.timeframe_consensus?.timeframe_weights} onChange={v => updEF('timeframe_consensus', 'timeframe_weights', v)} /></div>
      </Section>

      <Section title="session_context" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ef.session_context?.enabled} onChange={v => updEF('session_context', 'enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={ef.session_context?.mode} onChange={v => updEF('session_context', 'mode', v)} /></Field>
        <Field label="log_each_check"><Toggle value={ef.session_context?.log_each_check} onChange={v => updEF('session_context', 'log_each_check', v)} /></Field>
        {[['low_liquidity_start_hour_utc','h'],['low_liquidity_end_hour_utc','h'],['asian_start_hour_utc','h'],['asian_end_hour_utc','h'],['london_start_hour_utc','h'],['london_end_hour_utc','h'],['new_york_start_hour_utc','h'],['new_york_end_hour_utc','h'],['london_open_risk_minutes','min'],['new_york_open_risk_minutes','min'],['transition_risk_minutes','min'],['friday_cutoff_hour_utc','h']].map(([k, u]) => (
          <Field key={k} label={k} unit={u}><input type="number" step="1" value={ef.session_context?.[k] ?? ''} onChange={e => updEF('session_context', k, parseInt(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-16 text-right font-mono" /></Field>
        ))}
        {['scalping_timeframes','asia_preferred_currencies','london_preferred_currencies','new_york_preferred_currencies','high_noise_symbols'].map(k => (
          <div key={k} className="py-1"><div className="text-xs text-muted-foreground mb-1">{k}</div><ChipListEditor value={ef.session_context?.[k] || []} onChange={v => updEF('session_context', k, v)} /></div>
        ))}
      </Section>

      <Section title="market_regime" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ef.market_regime?.enabled} onChange={v => updEF('market_regime', 'enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={ef.market_regime?.mode} onChange={v => updEF('market_regime', 'mode', v)} /></Field>
        {['bars','atr_period','long_window','adx_period','efficiency_window','entropy_window'].map(k => (
          <Field key={k} label={k}><input type="number" step="1" value={ef.market_regime?.[k] ?? ''} onChange={e => updEF('market_regime', k, parseInt(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        {['compression_threshold','expansion_threshold','trend_adx_threshold','range_adx_threshold','panic_atr_percentile'].map(k => (
          <Field key={k} label={k}><input type="number" step="0.01" value={ef.market_regime?.[k] ?? ''} onChange={e => updEF('market_regime', k, parseFloat(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        <Field label="log_each_check"><Toggle value={ef.market_regime?.log_each_check} onChange={v => updEF('market_regime', 'log_each_check', v)} /></Field>
      </Section>

      <Section title="volatility_engine" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ef.volatility_engine?.enabled} onChange={v => updEF('volatility_engine', 'enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={ef.volatility_engine?.mode} onChange={v => updEF('volatility_engine', 'mode', v)} /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">block_states</div><ChipListEditor value={ef.volatility_engine?.block_states || []} onChange={v => updEF('volatility_engine', 'block_states', v)} /></div>
        {['bars','atr_period','short_window','long_window'].map(k => (
          <Field key={k} label={k}><input type="number" step="1" value={ef.volatility_engine?.[k] ?? ''} onChange={e => updEF('volatility_engine', k, parseInt(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        {['compression_threshold','expansion_threshold','panic_percentile','min_range_to_atr'].map(k => (
          <Field key={k} label={k}><input type="number" step="0.01" value={ef.volatility_engine?.[k] ?? ''} onChange={e => updEF('volatility_engine', k, parseFloat(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        <Field label="log_each_check"><Toggle value={ef.volatility_engine?.log_each_check} onChange={v => updEF('volatility_engine', 'log_each_check', v)} /></Field>
      </Section>

      <Section title="macro_flow" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ef.macro_flow?.enabled} onChange={v => updEF('macro_flow', 'enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={ef.macro_flow?.mode} onChange={v => updEF('macro_flow', 'mode', v)} /></Field>
        <Field label="aggregation"><input type="text" value={ef.macro_flow?.aggregation ?? ''} onChange={e => updEF('macro_flow', 'aggregation', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-32" /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">timeframes</div><ChipListEditor value={ef.macro_flow?.timeframes || []} onChange={v => updEF('macro_flow', 'timeframes', v)} /></div>
        {['bars','ema_fast','ema_slow','atr_period','momentum_bars'].map(k => (
          <Field key={k} label={k}><input type="number" step="1" value={ef.macro_flow?.[k] ?? ''} onChange={e => updEF('macro_flow', k, parseInt(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        <Field label="min_score"><input type="number" step="0.01" value={ef.macro_flow?.min_score ?? ''} onChange={e => updEF('macro_flow', 'min_score', parseFloat(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">weights</div><TFWeightsEditor weights={ef.macro_flow?.weights} onChange={v => updEF('macro_flow', 'weights', v)} /></div>
        <Field label="currency_strength.enabled"><Toggle value={ef.macro_flow?.currency_strength?.enabled} onChange={v => updEF('macro_flow', 'currency_strength', { ...ef.macro_flow?.currency_strength, enabled: v })} /></Field>
        <Field label="log_each_check"><Toggle value={ef.macro_flow?.log_each_check} onChange={v => updEF('macro_flow', 'log_each_check', v)} /></Field>
      </Section>

      <Section title="portfolio_correlation" defaultOpen={false}>
        <Field label="enabled"><Toggle value={ef.portfolio_correlation?.enabled} onChange={v => updEF('portfolio_correlation', 'enabled', v)} /></Field>
        <Field label="mode"><ModeSelect value={ef.portfolio_correlation?.mode} onChange={v => updEF('portfolio_correlation', 'mode', v)} /></Field>
        <Field label="matrix_path"><input type="text" value={ef.portfolio_correlation?.matrix_path ?? ''} onChange={e => updEF('portfolio_correlation', 'matrix_path', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-64" /></Field>
        {['min_abs_correlation','min_loss_money'].map(k => (
          <Field key={k} label={k}><input type="number" step="0.01" value={ef.portfolio_correlation?.[k] ?? ''} onChange={e => updEF('portfolio_correlation', k, parseFloat(e.target.value))} className="bg-secondary border border-border rounded px-2 py-1 text-xs w-20 text-right font-mono" /></Field>
        ))}
        {['log_passed_filter','block_same_risk_direction'].map(k => (
          <Field key={k} label={k}><Toggle value={ef.portfolio_correlation?.[k]} onChange={v => updEF('portfolio_correlation', k, v)} /></Field>
        ))}
        <Field label="reversal_relief.enabled"><Toggle value={ef.portfolio_correlation?.reversal_relief?.enabled} onChange={v => updEF('portfolio_correlation', 'reversal_relief', { ...ef.portfolio_correlation?.reversal_relief, enabled: v })} /></Field>
        <Field label="reversal_relief.mode"><ModeSelect value={ef.portfolio_correlation?.reversal_relief?.mode} onChange={v => updEF('portfolio_correlation', 'reversal_relief', { ...ef.portfolio_correlation?.reversal_relief, mode: v })} options={['allow', 'shadow', 'block', 'off']} /></Field>
      </Section>
    </div>
  );
}
import { Field, Toggle, NumInput, TextInput, Section } from '../FusionFieldRenderers';

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];

export default function TabDashboardLogs({ draft, set }) {
  const d = draft.dashboard || {};
  const eb = draft.event_bus || {};
  const lg = draft.logging || {};
  const updD = (k, v) => set('dashboard', { ...d, [k]: v });
  const updEB = (k, v) => set('event_bus', { ...eb, [k]: v });
  const updLG = (k, v) => set('logging', { ...lg, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="Dashboard">
        {['show_reason_column','show_reason_details','show_reason_summary','show_neutral_details','show_data_quality_details','show_market_structure_shadow'].map(k => (
          <Field key={k} label={k}><Toggle value={d[k]} onChange={v => updD(k, v)} /></Field>
        ))}
        <Field label="max_reason_items"><NumInput value={d.max_reason_items} onChange={v => updD('max_reason_items', v)} step={1} small /></Field>
        <Field label="max_summary_items"><NumInput value={d.max_summary_items} onChange={v => updD('max_summary_items', v)} step={1} small /></Field>
      </Section>

      <Section title="Event Bus">
        {['event_log_enabled','use_async','log_engine_results','log_tick_updates'].map(k => (
          <Field key={k} label={k}><Toggle value={eb[k]} onChange={v => updEB(k, v)} /></Field>
        ))}
        <Field label="event_log_dir"><TextInput value={eb.event_log_dir} onChange={v => updEB('event_log_dir', v)} wide /></Field>
        <Field label="async_stop_timeout" unit="s"><NumInput value={eb.async_stop_timeout} onChange={v => updEB('async_stop_timeout', v)} step={1} unit="s" small /></Field>
      </Section>

      <Section title="Logging">
        {['level', 'console_level'].map(k => (
          <Field key={k} label={k}>
            <select value={lg[k] || 'INFO'} onChange={e => updLG(k, e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
              {LOG_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </Field>
        ))}
        <Field label="log_dir"><TextInput value={lg.log_dir} onChange={v => updLG('log_dir', v)} wide /></Field>
        <Field label="max_file_size"><NumInput value={lg.max_file_size} onChange={v => updLG('max_file_size', v)} step={1024} /></Field>
        <Field label="backup_count"><NumInput value={lg.backup_count} onChange={v => updLG('backup_count', v)} step={1} small /></Field>
      </Section>
    </div>
  );
}
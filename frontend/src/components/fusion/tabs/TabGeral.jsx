import { Field, Toggle, NumInput, TextInput, ChipListEditor, KVTableEditor, ModeSelect, Section } from '../FusionFieldRenderers';

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'];

export default function TabGeral({ draft, set }) {
  const d = draft;
  return (
    <div className="space-y-2">
      <Section title="Geral">
        <Field label="enabled">
          <Toggle value={d.enabled} onChange={v => set('enabled', v)} />
        </Field>
        <Field label="loop.min_cycle_seconds" unit="s">
          <NumInput value={d.loop?.min_cycle_seconds} onChange={v => set('loop', { ...d.loop, min_cycle_seconds: v })} unit="s" step={1} min={1} small />
        </Field>
      </Section>

      <Section title="Símbolos Monitorados">
        <Field label="symbols">
          <ChipListEditor value={d.symbols || []} onChange={v => set('symbols', v)} />
        </Field>
      </Section>

      <Section title="Dados">
        <Field label="data.timeframe_default">
          <select value={d.data?.timeframe_default || 'H1'} onChange={e => set('data', { ...d.data, timeframe_default: e.target.value })}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {TIMEFRAMES.map(tf => <option key={tf} value={tf}>{tf}</option>)}
          </select>
        </Field>
        <Field label="data.data_dir">
          <TextInput value={d.data?.data_dir} onChange={v => set('data', { ...d.data, data_dir: v })} wide />
        </Field>
        <Field label="data.parquet_dir">
          <TextInput value={d.data?.parquet_dir} onChange={v => set('data', { ...d.data, parquet_dir: v })} wide />
        </Field>
        <div className="mt-2">
          <div className="text-xs text-muted-foreground mb-1">data.symbol_mapping (símbolo → broker)</div>
          <KVTableEditor value={d.data?.symbol_mapping || {}} onChange={v => set('data', { ...d.data, symbol_mapping: v })} />
        </div>
        <div className="mt-2">
          <div className="text-xs text-muted-foreground mb-1">data.point_values (símbolo → valor do ponto)</div>
          <KVTableEditor value={d.data?.point_values || {}} onChange={v => set('data', { ...d.data, point_values: v })} valueType="number" />
        </div>
      </Section>
    </div>
  );
}
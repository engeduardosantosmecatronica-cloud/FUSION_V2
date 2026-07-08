/**
 * Renderizadores genéricos de campos para o Fusion Control Center
 * Detectam o tipo pelo nome e tipo do valor
 */
import { cn } from '@/lib/utils';

const MODE_OPTIONS = ['block', 'shadow', 'off', 'monitor', 'allow'];
const MODE_COLORS = { block: 'text-red-400', shadow: 'text-yellow-400', off: 'text-muted-foreground', monitor: 'text-blue-400', allow: 'text-green-400' };

/** Toggle ON/OFF */
export function Toggle({ value, onChange, small }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={cn(
        'relative inline-flex shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none',
        small ? 'h-4 w-8' : 'h-5 w-9',
        value ? 'bg-green-500' : 'bg-muted'
      )}
    >
      <span className={cn(
        'pointer-events-none inline-block rounded-full bg-white shadow transform ring-0 transition duration-200',
        small ? 'h-3 w-3' : 'h-4 w-4',
        value ? (small ? 'translate-x-4' : 'translate-x-4') : 'translate-x-0'
      )} />
    </button>
  );
}

/** Seletor de modo block/shadow/off */
export function ModeSelect({ value, onChange, options = MODE_OPTIONS }) {
  return (
    <select
      value={value || 'off'}
      onChange={e => onChange(e.target.value)}
      className={cn('bg-secondary border border-border rounded px-2 py-1 text-xs', MODE_COLORS[value] || 'text-foreground')}
    >
      {options.map(o => (
        <option key={o} value={o} className="text-foreground bg-popover">{o}</option>
      ))}
    </select>
  );
}

/** Input numérico com unidade opcional */
export function NumInput({ value, onChange, unit, step = 0.01, min, max, small }) {
  return (
    <span className="flex items-center gap-1">
      <input
        type="number"
        value={value ?? ''}
        step={step}
        min={min}
        max={max}
        onChange={e => onChange(parseFloat(e.target.value))}
        className={cn(
          'bg-secondary border border-border rounded px-2 py-1 text-xs text-right font-mono',
          small ? 'w-16' : 'w-20'
        )}
      />
      {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
    </span>
  );
}

/** Input de texto */
export function TextInput({ value, onChange, placeholder, wide, type = 'text' }) {
  return (
    <input
      type={type}
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={cn(
        'bg-secondary border border-border rounded px-2 py-1 text-xs',
        wide ? 'w-full' : 'w-48'
      )}
    />
  );
}

/** Editor de lista de chips */
export function ChipListEditor({ value = [], onChange }) {
  return <ChipListEditorInner value={value} onChange={onChange} />;
}

/** Editor de tabela chave/valor */
export function KVTableEditor({ value = {}, onChange, valueType = 'text' }) {
  const entries = Object.entries(value);
  const update = (k, v) => onChange({ ...value, [k]: valueType === 'number' ? parseFloat(v) : v });
  const remove = (k) => { const n = { ...value }; delete n[k]; onChange(n); };
  const [nk, setNk] = useState('');
  const [nv, setNv] = useState('');
  const add = () => {
    if (nk.trim()) {
      onChange({ ...value, [nk.trim()]: valueType === 'number' ? parseFloat(nv) || 0 : nv });
      setNk(''); setNv('');
    }
  };
  return (
    <div className="space-y-1">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-1">
          <span className="text-xs font-mono text-muted-foreground w-24 truncate">{k}</span>
          <input
            type={valueType === 'number' ? 'number' : 'text'}
            value={v}
            onChange={e => update(k, e.target.value)}
            className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-24 font-mono"
          />
          <button onClick={() => remove(k)} className="text-xs text-red-400 hover:text-red-300">×</button>
        </div>
      ))}
      <div className="flex gap-1 mt-1">
        <input value={nk} onChange={e => setNk(e.target.value)} placeholder="Chave" className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-20" />
        <input value={nv} onChange={e => setNv(e.target.value)} placeholder="Valor" className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-20" />
        <button onClick={add} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">+</button>
      </div>
    </div>
  );
}

/** Linha de campo (label + controle) */
export function Field({ label, unit, children, indent }) {
  return (
    <div className={cn('flex items-center justify-between gap-2 py-1.5 border-b border-border/50 last:border-0', indent && 'pl-4')}>
      <span className={cn('text-xs shrink-0', unit ? 'text-foreground/70' : 'text-muted-foreground')}>{label}</span>
      <div className="flex items-center gap-1 shrink-0">{children}</div>
    </div>
  );
}

/** Seção com título */
export function Section({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded mb-3">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-bold text-muted-foreground uppercase bg-secondary/50 hover:bg-secondary"
      >
        {title}
        <span>{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-3 py-1">{children}</div>}
    </div>
  );
}

import React, { useState } from 'react';

// fix ChipListEditor to use useState
function ChipListEditorInner({ value = [], onChange }) {
  const [input, setInput] = useState('');
  const add = () => {
    if (input.trim() && !value.includes(input.trim())) {
      onChange([...value, input.trim()]);
      setInput('');
    }
  };
  const remove = (item) => onChange(value.filter(v => v !== item));
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap gap-1">
        {value.map(v => (
          <span key={v} className="flex items-center gap-1 px-2 py-0.5 bg-secondary border border-border rounded text-xs">
            {v}
            <button onClick={() => remove(v)} className="text-muted-foreground hover:text-red-400 leading-none">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-1">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="Adicionar..."
          className="bg-secondary border border-border rounded px-2 py-0.5 text-xs w-32"
        />
        <button onClick={add} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded hover:bg-primary/30">+</button>
      </div>
    </div>
  );
}

/** Renderizador genérico baseado em tipo/nome do campo */
export function GenericField({ path, name, value, onChange }) {
  const low = name.toLowerCase();

  // Boolean
  if (typeof value === 'boolean' || name === 'enabled' || low.includes('enabled') || low.startsWith('use_') || low.startsWith('allow_') || low.startsWith('require_') || low.startsWith('show_') || low.startsWith('block_') || low.startsWith('log_') || low.startsWith('write_') || low.startsWith('save_') || low.startsWith('auto_') || low.startsWith('fail_') || low.startsWith('only_')) {
    return (
      <Field label={name}>
        <Toggle value={!!value} onChange={onChange} small />
      </Field>
    );
  }

  // Mode selector
  if (name === 'mode' || low.endsWith('_mode') || low.endsWith('_filter') && typeof value === 'string' && MODE_OPTIONS.includes(value)) {
    return (
      <Field label={name}>
        <ModeSelect value={value} onChange={onChange} />
      </Field>
    );
  }

  // Number with unit hints
  if (typeof value === 'number') {
    const unit = low.includes('second') ? 's' : low.includes('minute') ? 'min' : low.includes('hour') ? 'h' : low.includes('pct') || low.includes('percent') || low.includes('rate') || low.includes('_pct') ? '%' : low.includes('day') ? 'd' : '';
    const isDecimal = low.includes('threshold') || low.includes('score') || low.includes('weight') || low.includes('confidence') || low.includes('pct') || low.includes('percent') || low.includes('rate');
    return (
      <Field label={name}>
        <NumInput value={value} onChange={onChange} unit={unit} step={isDecimal ? 0.01 : 1} small />
      </Field>
    );
  }

  // Array
  if (Array.isArray(value)) {
    return (
      <Field label={name}>
        <ChipListEditor value={value} onChange={onChange} />
      </Field>
    );
  }

  // String path/dir/file
  if (typeof value === 'string') {
    const isPath = low.includes('path') || low.includes('dir') || low.includes('file') || low.includes('url') || low.includes('endpoint');
    return (
      <Field label={name}>
        <TextInput value={value} onChange={onChange} wide={isPath} />
      </Field>
    );
  }

  // Object — render as group
  if (typeof value === 'object' && value !== null) {
    return (
      <Section title={name} defaultOpen={false}>
        {Object.entries(value).map(([k, v]) => (
          <GenericField
            key={k}
            path={path ? `${path}.${k}` : k}
            name={k}
            value={v}
            onChange={(newV) => onChange({ ...value, [k]: newV })}
          />
        ))}
      </Section>
    );
  }

  return (
    <Field label={name}>
      <TextInput value={value ?? ''} onChange={onChange} />
    </Field>
  );
}
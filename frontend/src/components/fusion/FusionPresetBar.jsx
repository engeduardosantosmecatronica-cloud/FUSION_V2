import { cn } from '@/lib/utils';

const PRESETS = [
  { key: 'conservador', label: 'Conservador', color: 'text-blue-400' },
  { key: 'normal', label: 'Normal', color: 'text-green-400' },
  { key: 'agressivo', label: 'Agressivo', color: 'text-orange-400' },
  { key: 'diagnostico', label: 'Diagnóstico', color: 'text-yellow-400' },
  { key: 'monitor_only', label: 'Só Monitor', color: 'text-muted-foreground' },
];

export default function FusionPresetBar({ onApply }) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <span className="text-xs text-muted-foreground">Presets:</span>
      {PRESETS.map(p => (
        <button
          key={p.key}
          onClick={() => onApply(p.key)}
          className={cn('text-xs px-3 py-1 bg-secondary border border-border rounded hover:bg-accent', p.color)}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
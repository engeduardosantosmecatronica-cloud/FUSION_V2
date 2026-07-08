import { useState } from 'react';
import { cn } from '@/lib/utils';

export default function FusionDiffViewer({ diff }) {
  const [open, setOpen] = useState(false);
  if (!diff || diff.length === 0) return null;

  return (
    <div className="mb-4 border border-yellow-800/50 rounded overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-yellow-950/30 text-xs text-yellow-400 font-medium hover:bg-yellow-950/50"
      >
        <span>Diff — {diff.length} campo{diff.length !== 1 ? 's' : ''} alterado{diff.length !== 1 ? 's' : ''}</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="divide-y divide-border max-h-64 overflow-y-auto">
          {diff.map((item, i) => (
            <div key={i} className="px-3 py-1.5 text-xs font-mono grid grid-cols-3 gap-2">
              <span className="text-muted-foreground truncate">{item.path}</span>
              <span className="text-red-400 truncate">{JSON.stringify(item.from)}</span>
              <span className="text-green-400 truncate">{JSON.stringify(item.to)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
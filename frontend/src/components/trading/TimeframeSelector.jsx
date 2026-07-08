import React from 'react';
import { cn } from '@/lib/utils';

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

export default function TimeframeSelector({ selected, onChange }) {
  return (
    <div className="flex items-center gap-1 px-4 py-2 border-b border-border bg-card/50">
      {TIMEFRAMES.map(tf => (
        <button
          key={tf}
          onClick={() => onChange(tf)}
          className={cn(
            "px-3 py-1 text-xs font-mono font-medium rounded transition-all",
            selected === tf
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-accent"
          )}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
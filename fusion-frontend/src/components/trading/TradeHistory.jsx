import React from 'react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

export default function TradeHistory({ trades }) {
  const closedTrades = trades.filter(t => t.status === 'closed').slice(0, 20);

  if (closedTrades.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground">
        Nenhum trade no histÃ³rico
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {closedTrades.map(trade => (
        <div key={trade.id} className="px-4 py-2.5 hover:bg-accent/50 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={cn(
                "text-[10px] font-mono px-1.5 py-0",
                trade.type === 'BUY' ? 'bg-green-600/20 text-green-400 border-green-600/30' : 'bg-red-600/20 text-red-400 border-red-600/30'
              )}>
                {trade.type}
              </span>
              <span className="text-xs font-medium">{trade.symbol}</span>
            </div>
            <span className={cn(
              "text-xs font-mono font-semibold",
              (trade.profit || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            )}>
              {(trade.profit || 0) >= 0 ? '+' : ''}{(trade.profit || 0).toFixed(2)}
            </span>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-[10px] text-muted-foreground font-mono">
              {trade.entry_price?.toFixed(5)} â†’ {trade.exit_price?.toFixed(5)}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {trade.closed_at ? format(new Date(trade.closed_at), 'dd/MM HH:mm') : ''}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

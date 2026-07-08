import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import { cn } from '@/lib/utils';

export default function OpenPositions({ trades, currentPrice }) {
  const openTrades = trades.filter(t => t.status === 'open');

  const handleClose = async (trade) => {
    const profit = trade.type === 'BUY'
      ? (currentPrice - trade.entry_price) * trade.lot_size * 100000
      : (trade.entry_price - currentPrice) * trade.lot_size * 100000;

    await base44.entities.Trade.update(trade.id, {
      status: 'closed',
      exit_price: currentPrice,
      profit: parseFloat(profit.toFixed(2)),
      closed_at: new Date().toISOString(),
    });
  };

  const calcPL = (trade) => {
    if (!currentPrice) return 0;
    return trade.type === 'BUY'
      ? (currentPrice - trade.entry_price) * trade.lot_size * 100000
      : (trade.entry_price - currentPrice) * trade.lot_size * 100000;
  };

  if (openTrades.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground">
        Nenhuma posição aberta
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {openTrades.map(trade => {
        const pl = calcPL(trade);
        const isProfit = pl >= 0;
        return (
          <div key={trade.id} className="px-4 py-2.5 flex items-center justify-between hover:bg-accent/50 transition-colors">
            <div className="flex items-center gap-3">
              <Badge className={cn(
                "text-[10px] font-mono px-1.5 py-0",
                trade.type === 'BUY' ? 'bg-green-600/20 text-green-400 border-green-600/30' : 'bg-red-600/20 text-red-400 border-red-600/30'
              )}>
                {trade.type}
              </Badge>
              <div>
                <p className="text-xs font-medium">{trade.symbol}</p>
                <p className="text-[10px] text-muted-foreground font-mono">
                  {trade.lot_size} lotes @ {trade.entry_price?.toFixed(5)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={cn(
                "text-xs font-mono font-semibold",
                isProfit ? 'text-green-400' : 'text-red-400'
              )}>
                {isProfit ? '+' : ''}{pl.toFixed(2)}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                onClick={() => handleClose(trade)}
              >
                <X className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
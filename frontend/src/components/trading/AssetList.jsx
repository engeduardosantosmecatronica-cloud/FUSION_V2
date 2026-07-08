import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Plus, X, Star, TrendingUp, TrendingDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';

const DEFAULT_WATCHLIST = [
  { symbol: 'EURUSD', category: 'Forex' },
  { symbol: 'GBPUSD', category: 'Forex' },
  { symbol: 'USDJPY', category: 'Forex' },
  { symbol: 'XAUUSD', category: 'Commodities' },
  { symbol: 'BTCUSD', category: 'Crypto' },
  { symbol: 'US500', category: 'Indices' },
];

export default function AssetList({ selected, onChange, lastPrices = {} }) {
  const [watchlist, setWatchlist] = useState(DEFAULT_WATCHLIST);
  const [adding, setAdding] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');

  const handleAdd = () => {
    const sym = newSymbol.trim().toUpperCase();
    if (sym && !watchlist.find(w => w.symbol === sym)) {
      setWatchlist(prev => [...prev, { symbol: sym, category: 'Custom' }]);
    }
    setNewSymbol('');
    setAdding(false);
  };

  const handleRemove = (symbol, e) => {
    e.stopPropagation();
    setWatchlist(prev => prev.filter(w => w.symbol !== symbol));
    if (selected === symbol && watchlist.length > 1) {
      onChange(watchlist.find(w => w.symbol !== symbol)?.symbol || '');
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-border flex items-center gap-2">
        <Star className="w-3.5 h-3.5 text-yellow-400" />
        <span className="text-xs font-semibold">Watchlist</span>
        <Button variant="ghost" size="icon" className="h-5 w-5 ml-auto" onClick={() => setAdding(true)}>
          <Plus className="w-3 h-3" />
        </Button>
      </div>

      {adding && (
        <div className="p-2 border-b border-border flex gap-1">
          <Input
            autoFocus
            value={newSymbol}
            onChange={e => setNewSymbol(e.target.value.toUpperCase())}
            onKeyDown={e => { if (e.key === 'Enter') handleAdd(); if (e.key === 'Escape') setAdding(false); }}
            placeholder="Ex: EURUSD"
            className="h-7 text-xs font-mono bg-muted border-border flex-1"
          />
          <Button size="sm" className="h-7 text-xs px-2" onClick={handleAdd}>+</Button>
        </div>
      )}

      <ScrollArea className="flex-1">
        {watchlist.map(({ symbol, category }) => {
          const priceData = lastPrices[symbol];
          const isSelected = selected === symbol;
          const change = priceData?.change || 0;
          const isUp = change >= 0;

          return (
            <button
              key={symbol}
              onClick={() => onChange(symbol)}
              className={cn(
                'w-full text-left px-3 py-2 flex items-center justify-between group transition-colors',
                isSelected ? 'bg-primary/10 border-l-2 border-primary' : 'hover:bg-accent/50 border-l-2 border-transparent'
              )}
            >
              <div>
                <p className={cn('text-xs font-mono font-semibold', isSelected ? 'text-primary' : 'text-foreground')}>
                  {symbol}
                </p>
                <p className="text-[9px] text-muted-foreground">{category}</p>
              </div>
              <div className="flex items-center gap-1">
                {priceData ? (
                  <div className="text-right">
                    <p className="text-[11px] font-mono">{priceData.price?.toFixed(5)}</p>
                    <div className={cn('flex items-center gap-0.5 text-[9px] justify-end', isUp ? 'text-green-400' : 'text-red-400')}>
                      {isUp ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                      {isUp ? '+' : ''}{change.toFixed(1)}%
                    </div>
                  </div>
                ) : (
                  <span className="text-[10px] text-muted-foreground font-mono">—</span>
                )}
                <Button
                  variant="ghost" size="icon"
                  className="h-4 w-4 opacity-0 group-hover:opacity-100 ml-1 text-muted-foreground hover:text-destructive"
                  onClick={(e) => handleRemove(symbol, e)}
                >
                  <X className="w-2.5 h-2.5" />
                </Button>
              </div>
            </button>
          );
        })}
      </ScrollArea>
    </div>
  );
}
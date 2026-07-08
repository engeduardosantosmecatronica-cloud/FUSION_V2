import React, { useEffect, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { fetchMt5LiveState } from '@/lib/mt5Api';

const DEFAULT_WATCHLIST = [
  { symbol: 'EURUSD', category: 'Forex' },
  { symbol: 'GBPUSD', category: 'Forex' },
  { symbol: 'USDJPY', category: 'Forex' },
  { symbol: 'GOLD', category: 'Commodities' },
  { symbol: 'BTCUSD', category: 'Crypto' },
  { symbol: 'AUDUSD', category: 'Forex' },
  { symbol: 'USDCAD', category: 'Forex' },
  { symbol: 'USDCHF', category: 'Forex' },
];

function priceDigits(symbol, price) {
  const s = String(symbol || '').toUpperCase();
  if (s.includes('BTC')) return 2;
  if (s.includes('JPY')) return 3;
  if (s.includes('GOLD') || s.includes('XAU')) return 2;
  return Number(price) > 100 ? 2 : 5;
}

function nextChange(prevPrice, nextPrice) {
  const prev = Number(prevPrice);
  const next = Number(nextPrice);
  if (!Number.isFinite(prev) || prev <= 0 || !Number.isFinite(next)) return 0;
  return ((next - prev) / prev) * 100;
}

export default function AssetList({ selected, onChange, lastPrices = {}, timeframe = 'M5' }) {
  const [watchlist, setWatchlist] = useState(DEFAULT_WATCHLIST);
  const [adding, setAdding] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [livePrices, setLivePrices] = useState({});
  const [updating, setUpdating] = useState(false);

  const symbols = useMemo(() => watchlist.map(w => w.symbol), [watchlist]);

  useEffect(() => {
    let cancelled = false;

    async function refreshAll() {
      if (!symbols.length) return;
      setUpdating(true);
      const results = await Promise.allSettled(
        symbols.map(async (sym) => {
          const payload = await fetchMt5LiveState(sym, timeframe || 'M5');
          const tickPrice = Number(payload?.tick?.bid || payload?.tick?.last || 0);
          const candlePrice = Number(payload?.current_candle?.close || 0);
          const price = tickPrice || candlePrice;
          return {
            symbol: sym,
            price,
            bid: Number(payload?.tick?.bid || 0),
            ask: Number(payload?.tick?.ask || 0),
            spread: Number(payload?.tick?.spread || 0),
            candle_time: payload?.current_candle?.time || '',
            source: payload?.source || '',
          };
        })
      );
      if (cancelled) return;
      setLivePrices(prev => {
        const next = { ...prev };
        for (const result of results) {
          if (result.status !== 'fulfilled') continue;
          const row = result.value;
          if (!Number.isFinite(row.price) || row.price <= 0) continue;
          const oldPrice = next[row.symbol]?.price ?? lastPrices[row.symbol]?.price;
          next[row.symbol] = {
            ...row,
            change: nextChange(oldPrice, row.price),
            updatedAt: new Date().toISOString(),
          };
        }
        return next;
      });
      setUpdating(false);
    }

    refreshAll();
    const id = setInterval(refreshAll, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [symbols.join('|'), timeframe]);

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
    const next = watchlist.filter(w => w.symbol !== symbol);
    setWatchlist(next);
    if (selected === symbol && next.length > 0) onChange(next[0].symbol);
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="px-3 py-2.5 border-b border-border flex items-center gap-2">
        <span className="text-yellow-400 text-xs" aria-hidden="true">★</span>
        <span className="text-xs font-semibold">Watchlist</span>
        <span className={cn('ml-auto text-[9px] font-mono', updating ? 'text-blue-400' : 'text-muted-foreground')}>{timeframe}</span>
        <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => setAdding(true)} title="Adicionar ativo">
          <span className="text-sm leading-none">+</span>
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

      <div className="flex-1 min-h-0 overflow-y-auto">
        {watchlist.map(({ symbol, category }) => {
          const priceData = livePrices[symbol] || lastPrices[symbol];
          const isSelected = selected === symbol;
          const change = Number(priceData?.change || 0);
          const isUp = change >= 0;
          const price = Number(priceData?.price);
          const digits = priceDigits(symbol, price);

          return (
            <button
              key={symbol}
              type="button"
              onClick={() => onChange(symbol)}
              className={cn(
                'w-full text-left px-3 py-2 flex items-center justify-between group transition-colors',
                isSelected ? 'bg-primary/10 border-l-2 border-primary' : 'hover:bg-accent/50 border-l-2 border-transparent'
              )}
            >
              <div className="min-w-0">
                <p className={cn('text-xs font-mono font-semibold truncate', isSelected ? 'text-primary' : 'text-foreground')}>{symbol}</p>
                <p className="text-[9px] text-muted-foreground truncate">{category}</p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {priceData ? (
                  <div className="text-right">
                    <p className="text-[11px] font-mono">{Number.isFinite(price) ? price.toFixed(digits) : '-'}</p>
                    <div className={cn('text-[9px]', isUp ? 'text-green-400' : 'text-red-400')}>
                      {isUp ? '▲ +' : '▼ '}{Math.abs(change).toFixed(3)}%
                    </div>
                    {Number(priceData.spread) > 0 && <div className="text-[8px] text-muted-foreground font-mono">sp {Number(priceData.spread).toFixed(1)}</div>}
                  </div>
                ) : <span className="text-[10px] text-muted-foreground font-mono">...</span>}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-4 w-4 opacity-0 group-hover:opacity-100 ml-1 text-muted-foreground hover:text-destructive"
                  onClick={(e) => handleRemove(symbol, e)}
                  title="Remover ativo"
                >
                  <span className="text-[10px] leading-none">x</span>
                </Button>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

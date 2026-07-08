import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const SYMBOLS = [
  { name: 'EURUSD', category: 'Forex' },
  { name: 'GBPUSD', category: 'Forex' },
  { name: 'USDJPY', category: 'Forex' },
  { name: 'AUDUSD', category: 'Forex' },
  { name: 'USDCAD', category: 'Forex' },
  { name: 'USDCHF', category: 'Forex' },
  { name: 'NZDUSD', category: 'Forex' },
  { name: 'XAUUSD', category: 'Commodities' },
  { name: 'XAGUSD', category: 'Commodities' },
  { name: 'BTCUSD', category: 'Crypto' },
  { name: 'ETHUSD', category: 'Crypto' },
  { name: 'US30', category: 'Indices' },
  { name: 'US500', category: 'Indices' },
  { name: 'NAS100', category: 'Indices' },
];

export default function SymbolSelector({ selected, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = SYMBOLS.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.category.toLowerCase().includes(search.toLowerCase())
  );

  const categories = [...new Set(filtered.map(s => s.category))];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" className="h-auto px-3 py-1 text-sm font-mono gap-1.5 hover:bg-accent">
          {selected}
          <span className="text-muted-foreground text-xs">v</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm bg-card border-border">
        <DialogHeader>
          <DialogTitle className="font-heading">Selecionar Ativo</DialogTitle>
        </DialogHeader>
        <div className="relative">
          <span className="absolute left-3 top-2.5 text-xs text-muted-foreground">?</span>
          <Input
            placeholder="Buscar..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9 h-9 text-sm bg-muted border-border"
          />
        </div>
        <div className="max-h-72 overflow-y-auto">
          {categories.map(cat => (
            <div key={cat}>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground px-2 pt-3 pb-1 font-semibold">{cat}</p>
              {filtered.filter(s => s.category === cat).map(s => (
                <button
                  key={s.name}
                  onClick={() => { onChange(s.name); setOpen(false); }}
                  className={cn(
                    "w-full text-left px-3 py-2 text-sm font-mono rounded-md transition-colors",
                    s.name === selected ? "bg-primary text-primary-foreground" : "hover:bg-accent text-foreground"
                  )}
                >
                  {s.name}
                </button>
              ))}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

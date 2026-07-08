import { useEffect, useState } from 'react';
import { getBlockAudit } from '@/services/api';
import { cn } from '@/lib/utils';

const SORT_OPTIONS = [
  { value: 'profit_lost', label: 'Maior lucro perdido' },
  { value: 'loss_avoided', label: 'Maior prejuízo evitado' },
  { value: 'filter', label: 'Filtro' },
  { value: 'symbol', label: 'Símbolo' },
  { value: 'timeframe', label: 'Timeframe' },
];

export default function Auditoria() {
  const [data, setData] = useState([]);
  const [sort, setSort] = useState('profit_lost');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBlockAudit().then(d => { setData(d); setLoading(false); });
  }, []);

  const sorted = [...data].sort((a, b) => {
    if (['profit_lost', 'loss_avoided'].includes(sort)) return b[sort] - a[sort];
    return String(a[sort]).localeCompare(String(b[sort]));
  });

  if (loading) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Auditoria de Bloqueios</h1>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Ordenar por:</span>
          <select value={sort} onChange={e => setSort(e.target.value)}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Símbolo','TF','Dir','Filtro','Preço Bloq.','Após 15m','Após 1h','Após 3h','Resultado (pts)','Classificação','Lucro Perdido','Prejuízo Evitado'].map(h => (
                <th key={h} className="px-2 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(r => (
              <tr key={r.id} className="border-b border-border hover:bg-accent">
                <td className="px-2 py-1.5 font-bold">{r.symbol}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{r.timeframe}</td>
                <td className={cn('px-2 py-1.5 font-bold', r.direction === 'BUY' ? 'text-green-400' : 'text-red-400')}>{r.direction}</td>
                <td className="px-2 py-1.5 font-mono text-xs">{r.filter}</td>
                <td className="px-2 py-1.5 font-mono">{r.price_at_block}</td>
                <td className="px-2 py-1.5 font-mono">{r.price_after_15m}</td>
                <td className="px-2 py-1.5 font-mono">{r.price_after_1h}</td>
                <td className="px-2 py-1.5 font-mono">{r.price_after_3h}</td>
                <td className={cn('px-2 py-1.5 font-mono font-bold', r.result_points >= 0 ? 'text-green-400' : 'text-red-400')}>
                  {r.result_points > 0 ? '+' : ''}{r.result_points}
                </td>
                <td className={cn('px-2 py-1.5 font-medium', r.classification === 'bom bloqueio' ? 'text-green-400' : 'text-red-400')}>
                  {r.classification}
                </td>
                <td className="px-2 py-1.5 font-mono text-red-400">{r.profit_lost.toFixed(2)}</td>
                <td className="px-2 py-1.5 font-mono text-green-400">{r.loss_avoided.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
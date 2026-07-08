import { useEffect, useState } from 'react';
import { getFilterStatus, updateFilterMode } from '@/services/api';
import { cn } from '@/lib/utils';

const MODE_COLOR = { block: 'text-red-400', shadow: 'text-yellow-400', off: 'text-muted-foreground' };
const REC_COLOR = { 'manter block': 'text-green-400', 'virar shadow': 'text-yellow-400', 'desligar': 'text-red-400' };

export default function Filtros() {
  const [filters, setFilters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getFilterStatus().then(f => { setFilters(f); setLoading(false); }); }, []);

  const changeMode = async (name, mode) => {
    await updateFilterMode(name, mode);
    setFilters(prev => prev.map(f => f.name === name ? { ...f, mode } : f));
  };

  if (loading) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  return (
    <div className="space-y-3">
      <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Painel de Filtros</h1>
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Filtro','Modo','Bloqueios','Bons','Maus','Lucro Perdido','Prejuízo Evitado','Recomendação','Último Motivo'].map(h => (
                <th key={h} className="px-2 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filters.map(f => (
              <tr key={f.name} className="border-b border-border hover:bg-accent">
                <td className="px-2 py-1.5 font-mono">{f.name}</td>
                <td className="px-2 py-1.5">
                  <select value={f.mode} onChange={e => changeMode(f.name, e.target.value)}
                    className={cn('bg-secondary border border-border rounded px-1 py-0.5 text-xs', MODE_COLOR[f.mode])}>
                    <option value="block">block</option>
                    <option value="shadow">shadow</option>
                    <option value="off">off</option>
                  </select>
                </td>
                <td className="px-2 py-1.5 font-mono text-right">{f.total_blocks}</td>
                <td className="px-2 py-1.5 font-mono text-green-400 text-right">{f.good_blocks}</td>
                <td className="px-2 py-1.5 font-mono text-red-400 text-right">{f.bad_blocks}</td>
                <td className="px-2 py-1.5 font-mono text-red-400 text-right">{f.profit_lost.toFixed(2)}</td>
                <td className="px-2 py-1.5 font-mono text-green-400 text-right">{f.loss_avoided.toFixed(2)}</td>
                <td className={cn('px-2 py-1.5 font-medium', REC_COLOR[f.recommendation])}>{f.recommendation}</td>
                <td className="px-2 py-1.5 text-muted-foreground max-w-40 truncate">{f.last_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
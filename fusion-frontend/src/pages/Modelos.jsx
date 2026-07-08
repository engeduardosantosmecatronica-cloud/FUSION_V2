import { useEffect, useState } from 'react';
import { getModelRegistry } from '@/services/api';
import { cn } from '@/lib/utils';

const STATUS_COLOR = { aprovado: 'text-green-400', reprovado: 'text-red-400', ausente: 'text-yellow-400' };

export default function Modelos() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getModelRegistry().then(m => { setModels(m); setLoading(false); }); }, []);

  if (loading) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  const byStatus = { aprovado: models.filter(m => m.status === 'aprovado'), reprovado: models.filter(m => m.status === 'reprovado'), ausente: models.filter(m => m.status === 'ausente') };

  return (
    <div className="space-y-4">
      <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Model Registry</h1>
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(byStatus).map(([status, list]) => (
          <div key={status} className="bg-card border border-border rounded p-3">
            <div className={cn('text-xs font-bold uppercase', STATUS_COLOR[status])}>{status}</div>
            <div className="text-2xl font-bold font-mono mt-1">{list.length}</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Modelo','Símbolo','TF','Versão','Status','Última Previsão','Conf. Média','Erro'].map(h => (
                <th key={h} className="px-2 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map(m => (
              <tr key={m.id} className="border-b border-border hover:bg-accent">
                <td className="px-2 py-1.5 font-mono text-xs">{m.name}</td>
                <td className="px-2 py-1.5 font-bold">{m.symbol}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{m.timeframe}</td>
                <td className="px-2 py-1.5 font-mono text-muted-foreground">{m.version}</td>
                <td className={cn('px-2 py-1.5 font-bold', STATUS_COLOR[m.status])}>{m.status}</td>
                <td className="px-2 py-1.5 font-mono text-muted-foreground">
                  {m.last_prediction ? new Date(m.last_prediction).toLocaleTimeString('pt-BR') : '—'}
                </td>
                <td className="px-2 py-1.5 font-mono">
                  {m.avg_confidence ? `${(m.avg_confidence * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="px-2 py-1.5 text-red-400 max-w-48 truncate" title={m.error}>{m.error || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
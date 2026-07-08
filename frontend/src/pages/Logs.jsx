import { useEffect, useState, useCallback } from 'react';
import { getLogs } from '@/services/api';
import { cn } from '@/lib/utils';
import { Copy, RefreshCw } from 'lucide-react';

const SEV_COLOR = { error: 'text-red-400', warn: 'text-yellow-400', info: 'text-muted-foreground' };
const TYPE_COLOR = {
  sinal: 'text-blue-400', ordem: 'text-green-400', bloqueio: 'text-yellow-400',
  erro: 'text-red-400', warning: 'text-orange-400', timing: 'text-muted-foreground',
};
const LOG_TYPES = ['', 'sinal', 'ordem', 'bloqueio', 'erro', 'warning', 'timing'];
const SYMBOLS = ['', 'EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'AUDUSD'];
const TIMEFRAMES = ['', 'M5', 'M15', 'M30', 'H1', 'H4'];

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({ type: '', symbol: '', timeframe: '', search: '' });
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    getLogs(filters).then(l => { setLogs(l); setLoading(false); });
  }, [filters]);

  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, [load]);

  const copy = (log) => {
    navigator.clipboard.writeText(`[${log.timestamp}] [${log.type}] ${log.message}`);
    setCopied(log.id);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="space-y-3 h-full flex flex-col">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Logs</h1>
        <button onClick={load} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Atualizar
        </button>
      </div>
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <input placeholder="Buscar..." value={filters.search} onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          className="bg-secondary border border-border rounded px-2 py-1 text-xs w-40" />
        {[
          { k: 'type', opts: LOG_TYPES, ph: 'Tipo' },
          { k: 'symbol', opts: SYMBOLS, ph: 'Símbolo' },
          { k: 'timeframe', opts: TIMEFRAMES, ph: 'TF' },
        ].map(({ k, opts, ph }) => (
          <select key={k} value={filters[k]} onChange={e => setFilters(f => ({ ...f, [k]: e.target.value }))}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            <option value="">{ph}</option>
            {opts.filter(Boolean).map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
      </div>
      {/* Log list */}
      <div className="flex-1 border border-border rounded overflow-y-auto bg-card font-mono text-xs">
        {logs.map(log => (
          <div key={log.id} className={cn(
            'flex items-start gap-2 px-3 py-1 border-b border-border hover:bg-accent group',
            log.severity === 'error' ? 'border-l-2 border-l-red-600' : log.severity === 'warn' ? 'border-l-2 border-l-yellow-600' : ''
          )}>
            <span className="text-muted-foreground shrink-0 w-20">{new Date(log.timestamp).toLocaleTimeString('pt-BR')}</span>
            <span className={cn('shrink-0 w-14', TYPE_COLOR[log.type])}>[{log.type}]</span>
            {log.symbol && <span className="text-blue-400 shrink-0">{log.symbol}</span>}
            {log.timeframe && <span className="text-muted-foreground shrink-0">{log.timeframe}</span>}
            <span className={cn('flex-1', SEV_COLOR[log.severity])}>{log.message}</span>
            <button onClick={() => copy(log)} className="opacity-0 group-hover:opacity-100 shrink-0 text-muted-foreground hover:text-foreground">
              {copied === log.id ? <span className="text-green-400">✓</span> : <Copy size={10} />}
            </button>
          </div>
        ))}
        {!loading && logs.length === 0 && (
          <div className="text-center text-muted-foreground py-8">Nenhum log encontrado</div>
        )}
      </div>
    </div>
  );
}
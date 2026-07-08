import { useEffect, useState, useCallback } from 'react';
import { getLiveSignals, getDecisionTimeline } from '@/services/api';
import { cn } from '@/lib/utils';
import { RefreshCw, X } from 'lucide-react';

const SYMBOLS = ['', 'EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'AUDUSD'];
const TIMEFRAMES = ['', 'M5', 'M15', 'M30', 'H1', 'H4'];
const STRATEGIES = ['', 'S1_trend', 'S2_reversal', 'S3_breakout'];

const STATUS_COLOR = {
  liberado: 'text-green-400', bloqueado: 'text-red-400', shadow: 'text-yellow-400', erro: 'text-orange-400',
};
const DIR_COLOR = { BUY: 'text-green-400', SELL: 'text-red-400', WAIT: 'text-muted-foreground' };

function TimelineModal({ signalId, onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => { getDecisionTimeline(signalId).then(setData); }, [signalId]);
  if (!data) return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded p-6 text-sm text-muted-foreground">Carregando...</div>
    </div>
  );
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-card border border-border rounded p-4 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase text-primary">Timeline da Decisão — {data.signal?.symbol} {data.signal?.timeframe}</span>
          <button onClick={onClose}><X size={14} /></button>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <Section title="Candle">
            {Object.entries(data.candle).map(([k, v]) => <Row key={k} k={k} v={v} />)}
          </Section>
          <Section title="Features">
            {Object.entries(data.features).map(([k, v]) => <Row key={k} k={k} v={v} />)}
          </Section>
          <Section title="Modelo">
            <Row k="nome" v={data.model.name} />
            <Row k="versão" v={data.model.version} />
            <Row k="p_buy" v={data.p_buy?.toFixed(3)} />
            <Row k="p_sell" v={data.p_sell?.toFixed(3)} />
          </Section>
          <Section title="Decisão">
            <Row k="estratégia" v={data.strategy} />
            <Row k="decisão" v={data.decision} />
            <Row k="ordem enviada" v={data.order_attempt?.sent ? 'sim' : 'não'} />
            <Row k="resultado MT5" v={data.mt5_result} />
          </Section>
          <Section title="Filtros Aplicados" className="col-span-2">
            <div className="grid grid-cols-3 gap-1 mt-1">
              {data.filters_applied?.map(f => (
                <span key={f.name} className={cn('text-xs px-1 py-0.5 rounded border', f.passed ? 'border-green-800 text-green-400' : 'border-red-800 text-red-400')}>
                  {f.name} [{f.mode}]
                </span>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
function Section({ title, children, className }) {
  return (
    <div className={cn('border border-border rounded p-2', className)}>
      <div className="text-xs font-bold text-muted-foreground mb-1 uppercase">{title}</div>
      {children}
    </div>
  );
}
function Row({ k, v }) {
  return <div className="flex justify-between gap-2 text-xs py-0.5"><span className="text-muted-foreground">{k}</span><span className="font-mono">{String(v)}</span></div>;
}

export default function Sinais() {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ symbol: '', timeframe: '', direction: '', status: '', strategy: '', min_confidence: '' });
  const [timeline, setTimeline] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    getLiveSignals(filters).then(s => { setSignals(s); setLoading(false); });
  }, [filters]);

  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);

  const F = ({ k, label, options }) => (
    <select value={filters[k]} onChange={e => setFilters(f => ({ ...f, [k]: e.target.value }))}
      className="bg-secondary border border-border rounded px-2 py-1 text-xs text-foreground">
      <option value="">{label}</option>
      {options.filter(Boolean).map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );

  return (
    <div className="space-y-3">
      {timeline && <TimelineModal signalId={timeline} onClose={() => setTimeline(null)} />}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Monitor de Sinais</h1>
        <button onClick={load} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Atualizar
        </button>
      </div>
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <F k="symbol" label="Símbolo" options={SYMBOLS} />
        <F k="timeframe" label="Timeframe" options={TIMEFRAMES} />
        <F k="direction" label="Direção" options={['', 'BUY', 'SELL', 'WAIT']} />
        <F k="status" label="Status" options={['', 'liberado', 'bloqueado', 'shadow', 'erro']} />
        <F k="strategy" label="Estratégia" options={STRATEGIES} />
        <input type="number" step="0.01" min="0" max="1" placeholder="Conf. mín." value={filters.min_confidence}
          onChange={e => setFilters(f => ({ ...f, min_confidence: e.target.value }))}
          className="bg-secondary border border-border rounded px-2 py-1 text-xs w-24" />
      </div>
      {/* Table */}
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Símbolo','TF','Decisão','p_buy','p_sell','Conf','Edge','Estratégia','Status','Motivo','Hora'].map(h => (
                <th key={h} className="px-2 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {signals.map(s => (
              <tr key={s.id} onClick={() => setTimeline(s.id)}
                className="border-b border-border hover:bg-accent cursor-pointer transition-colors">
                <td className="px-2 py-1.5 font-mono font-bold">{s.symbol}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{s.timeframe}</td>
                <td className={cn('px-2 py-1.5 font-bold', DIR_COLOR[s.decision])}>{s.decision}</td>
                <td className="px-2 py-1.5 font-mono">{s.p_buy.toFixed(3)}</td>
                <td className="px-2 py-1.5 font-mono">{s.p_sell.toFixed(3)}</td>
                <td className="px-2 py-1.5 font-mono">{(s.confidence * 100).toFixed(0)}%</td>
                <td className="px-2 py-1.5 font-mono">{s.edge.toFixed(3)}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{s.strategy}</td>
                <td className={cn('px-2 py-1.5 font-medium', STATUS_COLOR[s.status])}>{s.status}</td>
                <td className="px-2 py-1.5 text-muted-foreground max-w-32 truncate">{s.reason}</td>
                <td className="px-2 py-1.5 font-mono text-muted-foreground">{new Date(s.timestamp).toLocaleTimeString('pt-BR')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && signals.length === 0 && (
          <div className="text-center text-muted-foreground text-xs py-8">Nenhum sinal encontrado</div>
        )}
      </div>
    </div>
  );
}
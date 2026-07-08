import { cn } from '@/lib/utils';
import { format } from 'date-fns';

function directionConfig(signal) {
  const map = {
    BUY: { marker: '▲', color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/30', label: 'BUY' },
    SELL: { marker: '▼', color: 'text-red-400', bg: 'bg-red-400/10 border-red-400/30', label: 'SELL' },
  };
  return map[String(signal || '').toUpperCase()] || map.BUY;
}

function statusClass(status) {
  const s = String(status || '').toLowerCase();
  if (s.includes('liber') || s.includes('allow')) return 'text-green-400 border-green-500/25 bg-green-500/10';
  if (s.includes('shadow')) return 'text-yellow-400 border-yellow-500/25 bg-yellow-500/10';
  if (s.includes('bloq') || s.includes('block')) return 'text-red-400 border-red-500/25 bg-red-500/10';
  return 'text-slate-300 border-slate-500/20 bg-slate-500/10';
}

function confidencePct(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n <= 1 ? n * 100 : n));
}

function timeLabel(value) {
  if (!value) return '--:--';
  try { return format(new Date(value), 'HH:mm:ss'); }
  catch { return String(value).slice(11, 19) || '--:--'; }
}

function SignalRow({ signal }) {
  const direction = String(signal.decision || signal.signal || '').toUpperCase();
  const cfg = directionConfig(direction);
  const pct = confidencePct(signal.confidence ?? Math.max(Number(signal.p_buy || 0), Number(signal.p_sell || 0)));
  const reason = signal.reason || signal.raw_status || 'sem motivo informado';
  const status = signal.status || 'monitor';
  const barColor = direction === 'BUY' ? 'bg-green-500' : 'bg-red-500';

  return (
    <button type="button" className="w-full text-left rounded border border-border bg-[#0d1117]/80 hover:bg-[#111827] transition-colors p-2 space-y-1.5">
      <div className="min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <div className="text-sm font-bold text-white font-mono leading-tight whitespace-nowrap" title={`${signal.symbol} ${signal.timeframe}`}>
            {signal.symbol} <span className="text-[11px] text-muted-foreground font-sans">{signal.timeframe}</span>
          </div>
          <div className="text-[9px] text-muted-foreground font-mono shrink-0">{timeLabel(signal.timestamp || signal.updated_at)}</div>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <span className={cn('inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-bold', cfg.bg, cfg.color)}>
            <span>{cfg.marker}</span>{cfg.label}
          </span>
          <span className={cn('rounded border px-1.5 py-0.5 text-[9px] uppercase', statusClass(status))}>{status}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        <span className="font-mono">conf {pct.toFixed(0)}%</span>
        {signal.strategy ? <span>{signal.strategy}</span> : null}
      </div>
      <div className="h-1 bg-muted rounded overflow-hidden">
        <div className={cn('h-full rounded', barColor)} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-[10px] text-muted-foreground truncate" title={reason}>{reason}</div>
    </button>
  );
}

function signalTs(signal) {
  const raw = signal?.timestamp || signal?.updated_at || '';
  const t = raw ? new Date(raw).getTime() : 0;
  return Number.isFinite(t) ? t : 0;
}

function latestBySymbolTimeframe(signals) {
  const map = new Map();
  for (const signal of Array.isArray(signals) ? signals : []) {
    const direction = String(signal.decision || signal.signal || '').toUpperCase();
    if (!['BUY', 'SELL'].includes(direction)) continue;
    const key = `${signal.symbol || ''}:${signal.timeframe || ''}`;
    const previous = map.get(key);
    if (!previous || signalTs(signal) >= signalTs(previous)) map.set(key, signal);
  }
  return Array.from(map.values()).sort((a, b) => signalTs(b) - signalTs(a));
}

export default function SignalPanel({ signals = [] }) {
  const activeSignals = latestBySymbolTimeframe(signals).slice(0, 30);

  const buyCount = activeSignals.filter((s) => String(s.decision || s.signal || '').toUpperCase() === 'BUY').length;
  const sellCount = activeSignals.filter((s) => String(s.decision || s.signal || '').toUpperCase() === 'SELL').length;

  return (
    <div className="flex flex-col h-full min-h-0 rounded border border-border bg-[#0d1117]/40">
      <div className="px-3 py-2.5 border-b border-border flex items-center gap-2">
        <span className="text-yellow-400 text-xs" aria-hidden="true">⚡</span>
        <span className="text-xs font-semibold">Sinais Ativos</span>
        <span className="ml-auto text-[10px] font-mono text-green-400">B {buyCount}</span>
        <span className="text-[10px] font-mono text-red-400">S {sellCount}</span>
      </div>

      {activeSignals.length > 0 ? (
        <div className="p-2 space-y-2 max-h-[420px] overflow-y-auto">
          {activeSignals.map((signal, index) => (
            <SignalRow key={signal.id || `${signal.symbol}-${signal.timeframe}-${signal.timestamp}-${index}`} signal={signal} />
          ))}
        </div>
      ) : (
        <div className="p-4 text-center text-[11px] text-muted-foreground">Nenhum BUY/SELL real no momento</div>
      )}
    </div>
  );
}


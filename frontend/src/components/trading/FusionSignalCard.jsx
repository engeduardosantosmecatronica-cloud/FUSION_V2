import { useEffect, useState } from 'react';
import { getFusionSignalPanel } from '@/services/fusionSignalApi';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, RefreshCw, Clock, AlertTriangle } from 'lucide-react';

const STATUS_CONFIG = {
  allowed:   { label: 'LIBERADO',  color: 'text-green-400',  border: 'border-green-700', bg: 'bg-green-950/30' },
  blocked:   { label: 'BLOQUEADO', color: 'text-red-400',    border: 'border-red-700',   bg: 'bg-red-950/30' },
  shadow:    { label: 'SHADOW',    color: 'text-yellow-400', border: 'border-yellow-700', bg: 'bg-yellow-950/20' },
  wait:      { label: 'AGUARDAR', color: 'text-yellow-400', border: 'border-yellow-700/50', bg: '' },
  no_signal: { label: 'SEM SINAL', color: 'text-muted-foreground', border: 'border-border', bg: '' },
  error:     { label: 'ERRO',      color: 'text-red-400',    border: 'border-red-800',   bg: 'bg-red-950/30' },
  stale:     { label: 'DEFASADO',  color: 'text-orange-400', border: 'border-orange-700', bg: 'bg-orange-950/20' },
};

const SIGNAL_CONFIG = {
  BUY:  { label: 'COMPRAR', color: 'text-green-400', bg: 'bg-green-500/20 hover:bg-green-500/30', icon: TrendingUp },
  SELL: { label: 'VENDER',  color: 'text-red-400',   bg: 'bg-red-500/20 hover:bg-red-500/30', icon: TrendingDown },
  WAIT: { label: 'AGUARDAR', color: 'text-yellow-400', bg: 'bg-yellow-500/10', icon: Minus },
};

function ConfidenceBar({ value }) {
  const color = value >= 70 ? 'bg-green-500' : value >= 50 ? 'bg-yellow-400' : 'bg-red-500';
  return (
    <div className="h-1.5 bg-secondary rounded-full overflow-hidden w-full">
      <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${Math.min(100, value)}%` }} />
    </div>
  );
}

function PriceCard({ label, value, color }) {
  const dec = value > 100 ? 2 : value > 10 ? 3 : 5;
  return (
    <div className="flex flex-col items-center bg-secondary/60 rounded px-2 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn('text-sm font-mono font-bold', color)}>{value?.toFixed(dec) ?? '—'}</span>
    </div>
  );
}

export default function FusionSignalCard({ symbol, timeframe, compact }) {
  const [expanded, setExpanded] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    getFusionSignalPanel(symbol, timeframe)
      .then(setData)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [symbol, timeframe]);

  if (!data && loading) return (
    <div className="flex items-center justify-center p-4 text-muted-foreground text-xs">
      <RefreshCw size={12} className="animate-spin mr-2" /> Carregando sinal...
    </div>
  );

  if (!data) return null;

  const sig = SIGNAL_CONFIG[data.signal] || SIGNAL_CONFIG.WAIT;
  const SigIcon = sig.icon;
  const st = STATUS_CONFIG[data.status] || STATUS_CONFIG.no_signal;

  return (
    <div className={cn('border rounded p-3 space-y-2', st.border, st.bg)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-bold text-foreground">{data.symbol}</span>
          <span className="text-xs text-muted-foreground">{data.timeframe}</span>
          <span className={cn('text-xs font-medium px-1.5 py-0.5 rounded border', st.color, st.border, 'bg-transparent')}>{st.label}</span>
        </div>
        <button onClick={load} className="text-muted-foreground hover:text-foreground">
          <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Signal button */}
      <div className={cn('flex items-center justify-between rounded px-3 py-2', sig.bg)}>
        <div className="flex items-center gap-2">
          <SigIcon size={16} className={sig.color} />
          <span className={cn('text-sm font-bold', sig.color)}>{sig.label}</span>
          {data.strategy && <span className="text-xs text-muted-foreground">({data.strategy})</span>}
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock size={10} /> {data.analysis_time}
        </div>
      </div>

      {/* Confidence */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Confiança</span>
          <span className={cn('font-bold font-mono',
            data.confidence >= 70 ? 'text-green-400' : data.confidence >= 50 ? 'text-yellow-400' : 'text-red-400'
          )}>{data.confidence}%</span>
        </div>
        <ConfidenceBar value={data.confidence} />
      </div>

      {/* Price cards */}
      {data.signal !== 'WAIT' && (
        <div className="grid grid-cols-3 gap-1">
          <PriceCard label="Entrada" value={data.entry} color="text-foreground" />
          <PriceCard label="Stop Loss" value={data.stop_loss} color="text-red-400" />
          <PriceCard label="Take Profit" value={data.take_profit} color="text-green-400" />
        </div>
      )}

      {/* Probability bars */}
      {!compact && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="flex justify-between mb-0.5"><span className="text-muted-foreground">P(Buy)</span><span className="text-green-400 font-mono">{(data.p_buy * 100).toFixed(0)}%</span></div>
            <div className="h-1 bg-secondary rounded-full"><div className="h-full bg-green-500 rounded-full" style={{ width: `${data.p_buy * 100}%` }} /></div>
          </div>
          <div>
            <div className="flex justify-between mb-0.5"><span className="text-muted-foreground">P(Sell)</span><span className="text-red-400 font-mono">{(data.p_sell * 100).toFixed(0)}%</span></div>
            <div className="h-1 bg-secondary rounded-full"><div className="h-full bg-red-500 rounded-full" style={{ width: `${data.p_sell * 100}%` }} /></div>
          </div>
        </div>
      )}

      {/* S/R levels */}
      {!compact && data.signal !== 'WAIT' && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="text-muted-foreground mb-0.5">Suporte</div>
            {(data.support_levels || []).map((p, i) => {
              const dec = p > 100 ? 2 : p > 10 ? 3 : 5;
              return <div key={i} className="font-mono text-green-400/70">S{i+1}: {p?.toFixed(dec)}</div>;
            })}
          </div>
          <div>
            <div className="text-muted-foreground mb-0.5">Resistência</div>
            {(data.resistance_levels || []).map((p, i) => {
              const dec = p > 100 ? 2 : p > 10 ? 3 : 5;
              return <div key={i} className="font-mono text-red-400/70">R{i+1}: {p?.toFixed(dec)}</div>;
            })}
          </div>
        </div>
      )}

      {/* Reason and historical decision */}
      <div className="text-xs text-muted-foreground border-t border-border/50 pt-1.5">
        <div className="flex items-start gap-1">
          <AlertTriangle size={10} className="shrink-0 mt-0.5 text-yellow-400/60" />
          <span className="leading-relaxed">{data.reason}</span>
        </div>

        { (data.historical_decision || data.historical_decision_gate) && (
          <div className="mt-2">
            {(() => {
              const hd = data.historical_decision || data.historical_decision_gate || {};
              const dec = (hd.decision || hd.direction || 'hold').toLowerCase();
              const conf = Math.round((hd.confidence || hd.confidence === 0) ? Number(hd.confidence) : (hd.confidence_pct || 0));
              const cls = dec === 'buy' ? 'text-green-400' : dec === 'sell' ? 'text-red-400' : 'text-muted-foreground';
              return (
                <div className="flex items-center justify-between">
                  <div className={cn('flex items-center gap-2 font-mono text-sm', cls)}>
                    <span className="font-bold">{dec.toUpperCase()}</span>
                    <div className="text-[11px] text-muted-foreground">{conf}%</div>
                    {hd.positive_factors && hd.positive_factors.length > 0 && (
                      <div className="text-[11px] text-muted-foreground ml-2">+{hd.positive_factors.slice(0,3).join(', ')}</div>
                    )}
                  </div>
                  <button onClick={() => setExpanded(!expanded)} className="text-[11px] text-muted-foreground underline">
                    {expanded ? 'Ocultar detalhes' : 'Ver detalhes'}
                  </button>
                </div>
              );
            })()}

            {expanded && (() => {
              const hd = data.historical_decision || data.historical_decision_gate || {};
              const features = hd.features || {};
              return (
                <div className="mt-2 text-[12px] text-muted-foreground">
                  <div><strong>Acceptance:</strong> {features.acceptance_status || '—'}</div>
                  <div><strong>Zone:</strong> {(features.zone && features.zone.type) || ((features.zone && features.zone.type) ? features.zone.type : (features.zone && features.zone.type) ? features.zone.type : (features.zone && features.zone.zone_type) || '—')}</div>
                  <div><strong>Recency:</strong> {features.recency || '—'}</div>
                  <div className="mt-1"><strong>Confidence breakdown:</strong></div>
                  <div className="text-xs font-mono">{JSON.stringify(hd.details || features || {}, null, 2)}</div>
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
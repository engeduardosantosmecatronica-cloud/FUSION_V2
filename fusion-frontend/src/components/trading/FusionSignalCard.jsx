import { useEffect, useState, useCallback } from 'react';
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

const numeric = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

function ConfidenceBar({ value }) {
  const safeValue = Math.max(0, Math.min(100, numeric(value)));
  const color = safeValue >= 70 ? 'bg-green-500' : safeValue >= 50 ? 'bg-yellow-400' : 'bg-red-500';
  return <div className="h-1.5 bg-secondary rounded-full overflow-hidden w-full"><div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${safeValue}%` }} /></div>;
}

function PriceCard({ label, value, color }) {
  const price = numeric(value, NaN);
  const dec = price > 100 ? 2 : price > 10 ? 3 : 5;
  return (
    <div className="flex flex-col items-center bg-secondary/60 rounded px-2 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn('text-sm font-mono font-bold', color)}>{Number.isFinite(price) && price > 0 ? price.toFixed(dec) : '-'}</span>
    </div>
  );
}

export default function FusionSignalCard({ symbol, timeframe, compact }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    getFusionSignalPanel(symbol, timeframe)
      .then((payload) => setData(payload || null))
      .catch((err) => setError(err?.message || 'Falha ao carregar sinal'))
      .finally(() => setLoading(false));
  }, [symbol, timeframe]);

  useEffect(() => { load(); }, [load]);

  const safeData = data || {
    symbol,
    timeframe,
    signal: 'WAIT',
    status: error ? 'error' : 'no_signal',
    confidence: 0,
    analysis_time: '--:--:--',
    reason: error || (loading ? 'Carregando sinal do Fusion...' : 'Sem sinal carregado'),
    p_buy: 0,
    p_sell: 0,
    support_levels: [],
    resistance_levels: [],
  };

  const signal = String(safeData.signal || 'WAIT').toUpperCase();
  const pBuy = numeric(safeData.p_buy);
  const pSell = numeric(safeData.p_sell);
  const dominantSide = pBuy > pSell ? 'BUY' : pSell > pBuy ? 'SELL' : 'WAIT';
  const dominantProb = Math.max(pBuy, pSell);
  const hasDominantBlockedSide = signal === 'WAIT' && dominantSide !== 'WAIT' && dominantProb >= 0.6;
  const displaySignal = hasDominantBlockedSide ? dominantSide : signal;
  const sig = SIGNAL_CONFIG[displaySignal] || SIGNAL_CONFIG.WAIT;
  const SigIcon = sig.icon;
  const st = STATUS_CONFIG[safeData.status] || STATUS_CONFIG.no_signal;
  const confidence = numeric(safeData.confidence);
  const supportLevels = Array.isArray(safeData.support_levels) ? safeData.support_levels : [];
  const resistanceLevels = Array.isArray(safeData.resistance_levels) ? safeData.resistance_levels : [];

  return (
    <div className={cn('border rounded p-3 space-y-2', st.border, st.bg)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-xs font-bold text-foreground truncate">{safeData.symbol}</span>
          <span className="text-xs text-muted-foreground">{safeData.timeframe}</span>
          <span className={cn('text-xs font-medium px-1.5 py-0.5 rounded border', st.color, st.border, 'bg-transparent')}>{st.label}</span>
        </div>
        <button type="button" onClick={load} className="text-muted-foreground hover:text-foreground shrink-0" title="Atualizar sinal">
          <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className={cn('flex items-center justify-between rounded px-3 py-2', sig.bg)}>
        <div className="flex items-center gap-2 min-w-0">
          <SigIcon size={16} className={sig.color} />
          <span className={cn('text-sm font-bold', sig.color)}>{hasDominantBlockedSide ? `${sig.label} BLOQUEADO` : sig.label}</span>
          {safeData.strategy ? <span className="text-xs text-muted-foreground truncate">({safeData.strategy})</span> : null}
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <Clock size={10} /> {safeData.analysis_time || '--:--:--'}
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{hasDominantBlockedSide ? 'Probabilidade dominante' : signal === 'WAIT' ? 'Confianca WAIT' : 'Confianca'}</span>
          <span className={cn('font-bold font-mono', confidence >= 70 ? 'text-green-400' : confidence >= 50 ? 'text-yellow-400' : 'text-red-400')}>
            {hasDominantBlockedSide ? `${dominantSide} ${(dominantProb * 100).toFixed(0)}%` : `${confidence.toFixed(0)}%`}
          </span>
        </div>
        <ConfidenceBar value={hasDominantBlockedSide ? dominantProb * 100 : confidence} />
        {hasDominantBlockedSide && (
          <div className="text-[10px] text-yellow-400/90 leading-relaxed">
            Decisao final WAIT, mas o modelo favorece {dominantSide}. Aguardando filtro/confirmacao.
          </div>
        )}
      </div>

      {signal !== 'WAIT' && (
        <div className="grid grid-cols-3 gap-1">
          <PriceCard label="Entrada" value={safeData.entry} color="text-foreground" />
          <PriceCard label="Stop Loss" value={safeData.stop_loss} color="text-red-400" />
          <PriceCard label="Take Profit" value={safeData.take_profit} color="text-green-400" />
        </div>
      )}

      {!compact && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="flex justify-between mb-0.5"><span className="text-muted-foreground">P(Buy)</span><span className="text-green-400 font-mono">{(pBuy * 100).toFixed(0)}%</span></div>
            <div className="h-1 bg-secondary rounded-full"><div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.max(0, Math.min(100, pBuy * 100))}%` }} /></div>
          </div>
          <div>
            <div className="flex justify-between mb-0.5"><span className="text-muted-foreground">P(Sell)</span><span className="text-red-400 font-mono">{(pSell * 100).toFixed(0)}%</span></div>
            <div className="h-1 bg-secondary rounded-full"><div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.max(0, Math.min(100, pSell * 100))}%` }} /></div>
          </div>
        </div>
      )}

      {!compact && (supportLevels.length > 0 || resistanceLevels.length > 0) && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="text-muted-foreground mb-0.5">Suporte</div>
            {supportLevels.map((p, i) => {
              const price = numeric(p, NaN);
              const dec = price > 100 ? 2 : price > 10 ? 3 : 5;
              return <div key={`s-${i}`} className="font-mono text-green-400/70">S{i + 1}: {Number.isFinite(price) ? price.toFixed(dec) : '-'}</div>;
            })}
          </div>
          <div>
            <div className="text-muted-foreground mb-0.5">Resistencia</div>
            {resistanceLevels.map((p, i) => {
              const price = numeric(p, NaN);
              const dec = price > 100 ? 2 : price > 10 ? 3 : 5;
              return <div key={`r-${i}`} className="font-mono text-red-400/70">R{i + 1}: {Number.isFinite(price) ? price.toFixed(dec) : '-'}</div>;
            })}
          </div>
        </div>
      )}

      <div className="text-xs text-muted-foreground border-t border-border/50 pt-1.5 flex items-start gap-1">
        <AlertTriangle size={10} className="shrink-0 mt-0.5 text-yellow-400/60" />
        <span className="leading-relaxed break-words">{safeData.reason || 'Sem motivo informado'}</span>
      </div>
    </div>
  );
}

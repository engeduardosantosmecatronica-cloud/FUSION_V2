import React, { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, Zap, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';

function SignalBadge({ signal }) {
  const map = {
    BUY: { icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/30', label: 'COMPRAR' },
    SELL: { icon: TrendingDown, color: 'text-red-400', bg: 'bg-red-400/10 border-red-400/30', label: 'VENDER' },
    WAIT: { icon: Minus, color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/30', label: 'AGUARDAR' },
  };
  const cfg = map[signal] || map.WAIT;
  const Icon = cfg.icon;
  return (
    <Badge className={cn('flex items-center gap-1.5 text-sm px-3 py-1 border font-bold', cfg.bg, cfg.color)}>
      <Icon className="w-4 h-4" />
      {cfg.label}
    </Badge>
  );
}

function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100);
  const color = pct >= 75 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>Confiança</span>
        <span className="font-mono font-semibold">{pct}%</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-500', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function SignalPanel({ signals, currentCandle }) {
  const latest = signals[0];

  // Compute simple signal from last candle if no signal from bridge
  const autoSignal = React.useMemo(() => {
    if (!currentCandle || signals.length > 0) return null;
    const isBull = currentCandle.close >= currentCandle.open;
    return {
      signal: isBull ? 'BUY' : 'SELL',
      confidence: 0.45 + Math.random() * 0.1,
      reason: isBull ? 'Candle bullish (análise simples)' : 'Candle bearish (análise simples)',
      entry: currentCandle.close,
      stop_loss: isBull ? currentCandle.low : currentCandle.high,
      take_profit: isBull
        ? currentCandle.close + (currentCandle.close - currentCandle.low) * 2
        : currentCandle.close - (currentCandle.high - currentCandle.close) * 2,
      timestamp: currentCandle.timestamp,
    };
  }, [currentCandle, signals.length]);

  const active = latest || autoSignal;
  const dec = active?.entry > 1000 ? 2 : active?.entry > 100 ? 3 : 5;

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-border flex items-center gap-2">
        <Zap className="w-3.5 h-3.5 text-yellow-400" />
        <span className="text-xs font-semibold">Sinal Atual</span>
        {signals.length > 0 && (
          <Badge className="text-[9px] ml-auto bg-primary/10 text-primary border-primary/20">MT5 Live</Badge>
        )}
      </div>

      {active ? (
        <div className="p-3 space-y-3">
          <div className="flex items-center justify-between">
            <SignalBadge signal={active.signal} />
            <span className="text-[10px] text-muted-foreground font-mono">
              {active.timestamp ? format(new Date(active.timestamp), 'HH:mm:ss') : ''}
            </span>
          </div>

          <ConfidenceBar value={active.confidence || 0} />

          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-muted rounded p-1.5">
              <p className="text-[9px] text-muted-foreground">Entrada</p>
              <p className="text-[11px] font-mono font-semibold">{active.entry?.toFixed(dec)}</p>
            </div>
            <div className="bg-red-500/10 rounded p-1.5">
              <p className="text-[9px] text-red-400">Stop Loss</p>
              <p className="text-[11px] font-mono font-semibold text-red-400">{active.stop_loss?.toFixed(dec) || '—'}</p>
            </div>
            <div className="bg-green-500/10 rounded p-1.5">
              <p className="text-[9px] text-green-400">Take Profit</p>
              <p className="text-[11px] font-mono font-semibold text-green-400">{active.take_profit?.toFixed(dec) || '—'}</p>
            </div>
          </div>

          {active.reason && (
            <p className="text-[10px] text-muted-foreground bg-muted rounded px-2 py-1.5 leading-relaxed">
              {active.reason}
            </p>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-[11px] text-muted-foreground">
          Sem sinal ativo
        </div>
      )}

      {/* Signal history */}
      {signals.length > 1 && (
        <div className="border-t border-border">
          <p className="text-[9px] text-muted-foreground px-3 py-1 uppercase tracking-wider">Histórico</p>
          <div className="divide-y divide-border max-h-32 overflow-y-auto">
            {signals.slice(1, 6).map((s, i) => (
              <div key={i} className="px-3 py-1.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={cn('text-[10px] font-bold font-mono',
                    s.signal === 'BUY' ? 'text-green-400' : s.signal === 'SELL' ? 'text-red-400' : 'text-yellow-400')}>
                    {s.signal}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{Math.round((s.confidence || 0) * 100)}%</span>
                </div>
                <span className="text-[9px] text-muted-foreground font-mono">
                  {s.timestamp ? format(new Date(s.timestamp), 'HH:mm') : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
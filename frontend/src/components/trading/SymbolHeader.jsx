import React from 'react';
import { TrendingUp, TrendingDown, Wifi, WifiOff } from 'lucide-react';

export default function SymbolHeader({ symbol, candles, isConnected }) {
  const lastCandle = candles[candles.length - 1];
  const prevCandle = candles.length > 1 ? candles[candles.length - 2] : null;

  const currentPrice = lastCandle?.close || 0;
  const change = prevCandle ? currentPrice - prevCandle.close : 0;
  const changePercent = prevCandle && prevCandle.close ? (change / prevCandle.close) * 100 : 0;
  const isPositive = change >= 0;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <h2 className="text-lg font-bold font-heading tracking-tight">{symbol}</h2>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xl font-mono font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {currentPrice.toFixed(5)}
          </span>
          <div className={`flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded ${isPositive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            <span>{isPositive ? '+' : ''}{change.toFixed(5)}</span>
            <span>({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs font-mono">
        {isConnected ? (
          <div className="flex items-center gap-1.5 text-green-400">
            <Wifi className="w-3.5 h-3.5" />
            <span>Conectado</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-red-400">
            <WifiOff className="w-3.5 h-3.5" />
            <span>Desconectado</span>
          </div>
        )}
      </div>
    </div>
  );
}
import React from 'react';
import { cn } from '@/lib/utils';

const STATUS_CONFIG = {
  connected: { marker: '●', color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/20', label: 'MT5 Live' },
  connecting: { marker: '●', color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/20', label: 'Conectando' },
  disconnected: { marker: '●', color: 'text-red-400', bg: 'bg-red-400/10 border-red-400/20', label: 'Sem WS' },
  error: { marker: '!', color: 'text-orange-400', bg: 'bg-orange-400/10 border-orange-400/20', label: 'Erro' },
  demo: { marker: '●', color: 'text-blue-400', bg: 'bg-blue-400/10 border-blue-400/20', label: 'Demo' },
  direct: { marker: '●', color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/20', label: 'MT5 Direto' },
};

export default function FeedStatus({ wsStatus, latency, feedMode, candleCount }) {
  const key = feedMode === 'live' ? 'direct' : feedMode === 'demo' ? 'demo' : wsStatus;
  const cfg = STATUS_CONFIG[key] || STATUS_CONFIG.disconnected;
  const count = Number.isFinite(Number(candleCount)) ? Number(candleCount) : 0;

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 border-b border-border bg-card/50 text-[11px] font-mono">
      <span className={cn('inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-semibold', cfg.bg, cfg.color)}>
        <span aria-hidden="true">{cfg.marker}</span>
        <span>{cfg.label}</span>
      </span>

      {latency !== null && wsStatus === 'connected' && (
        <span className={cn('text-[10px]', latency < 10 ? 'text-green-400' : latency < 50 ? 'text-yellow-400' : 'text-red-400')}>
          {latency}ms
        </span>
      )}

      <span className="text-[#6e7681]">{count} velas</span>
      <span className="text-[#6e7681]">API MT5 direta</span>
    </div>
  );
}

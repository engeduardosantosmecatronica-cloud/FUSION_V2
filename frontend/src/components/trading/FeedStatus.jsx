import React from 'react';
import { cn } from '@/lib/utils';
import { Wifi, WifiOff, Loader2, AlertTriangle, Radio } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const STATUS_CONFIG = {
  connected: { icon: Wifi, color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/20', label: 'MT5 Live' },
  connecting: { icon: Loader2, color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/20', label: 'Conectando...', spin: true },
  disconnected: { icon: WifiOff, color: 'text-red-400', bg: 'bg-red-400/10 border-red-400/20', label: 'Desconectado' },
  error: { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-400/10 border-orange-400/20', label: 'Erro WS' },
  demo: { icon: Radio, color: 'text-blue-400', bg: 'bg-blue-400/10 border-blue-400/20', label: 'Demo' },
};

export default function FeedStatus({ wsStatus, latency, feedMode, candleCount }) {
  const cfg = STATUS_CONFIG[feedMode === 'demo' ? 'demo' : wsStatus] || STATUS_CONFIG.disconnected;
  const Icon = cfg.icon;

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 border-b border-border bg-card/50 text-[11px] font-mono">
      <Badge className={cn('flex items-center gap-1.5 text-[10px] px-2 py-0.5 border', cfg.bg, cfg.color)}>
        <Icon className={cn('w-3 h-3', cfg.spin && 'animate-spin')} />
        {cfg.label}
      </Badge>

      {latency !== null && wsStatus === 'connected' && (
        <span className={cn('text-[10px]', latency < 10 ? 'text-green-400' : latency < 50 ? 'text-yellow-400' : 'text-red-400')}>
          {latency}ms
        </span>
      )}

      <span className="text-[#6e7681]">
        {candleCount} velas
      </span>

      {wsStatus === 'disconnected' && feedMode !== 'demo' && (
        <span className="text-orange-400/70">
          Bridge local não encontrado — use modo Demo ou inicie bridge_server.py
        </span>
      )}
    </div>
  );
}
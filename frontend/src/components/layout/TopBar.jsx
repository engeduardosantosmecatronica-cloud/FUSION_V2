import { useEffect, useState } from 'react';
import { getSystemStatus } from '@/services/api';
import { cn } from '@/lib/utils';
import { Wifi, WifiOff, Activity, AlertTriangle, Clock } from 'lucide-react';

function Dot({ ok, label }) {
  return (
    <span className="flex items-center gap-1 text-xs">
      <span className={cn('w-1.5 h-1.5 rounded-full', ok ? 'bg-green-400' : 'bg-red-400')} />
      <span className={ok ? 'text-green-400' : 'text-red-400'}>{label}</span>
    </span>
  );
}

export default function TopBar() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    getSystemStatus().then(setStatus);
    const id = setInterval(() => getSystemStatus().then(setStatus), 10000);
    return () => clearInterval(id);
  }, []);

  const now = new Date().toLocaleTimeString('pt-BR');

  return (
    <header className="flex items-center gap-4 px-4 py-2 bg-card border-b border-border text-xs shrink-0">
      <span className="font-bold text-primary tracking-wider mr-2">FUSION COCKPIT</span>
      {status ? (
        <>
          <Dot ok={status.fusion?.status === 'online'} label="Fusion" />
          <Dot ok={status.mt5?.status === 'online'} label="MT5" />
          <Dot ok={status.backend?.status === 'online'} label="API" />
          <Dot ok={status.feed?.status === 'online'} label="Feed" />
          <span className="text-muted-foreground ml-2 flex items-center gap-1">
            <Activity size={10} /> {status.simulated_latency_ms}ms
          </span>
          <span className="text-muted-foreground flex items-center gap-1">
            <AlertTriangle size={10} className="text-yellow-400" />
            {status.open_orders} ordens
          </span>
          <span className="ml-auto text-muted-foreground flex items-center gap-1">
            <Clock size={10} /> {now}
          </span>
        </>
      ) : (
        <span className="text-muted-foreground">Carregando status...</span>
      )}
    </header>
  );
}
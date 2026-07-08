import { useEffect, useState } from 'react';
import { getSystemStatus, getAlerts } from '@/services/api';
import { cn } from '@/lib/utils';
import { Activity, AlertTriangle, Clock, Cpu, Database, Wifi, Zap } from 'lucide-react';

function StatusCard({ label, value, ok, sub }) {
  return (
    <div className="bg-card border border-border rounded p-3 flex flex-col gap-1">
      <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className={cn('text-sm font-bold', ok === true ? 'text-green-400' : ok === false ? 'text-red-400' : 'text-foreground')}>
        {value}
      </span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

export default function SystemDashboard() {
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    getSystemStatus().then(setStatus);
    getAlerts().then(setAlerts);
    const id = setInterval(() => getSystemStatus().then(setStatus), 8000);
    return () => clearInterval(id);
  }, []);

  if (!status) return <div className="text-muted-foreground text-sm p-8">Carregando...</div>;

  const unacked = alerts.filter(a => !a.acknowledged);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Dashboard do Sistema</h1>
        <span className="text-xs text-yellow-400 flex items-center gap-1"><AlertTriangle size={10} /> MOCK MODE</span>
      </div>

      {/* Status grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
        <StatusCard label="Fusion" value={status.fusion.status.toUpperCase()} ok={status.fusion.status === 'online'} sub={`Ciclo: ${status.fusion.cycle_duration_ms}ms`} />
        <StatusCard label="MT5" value={status.mt5.status.toUpperCase()} ok={status.mt5.status === 'online'} sub={status.mt5.account} />
        <StatusCard label="Backend/API" value={status.backend.status.toUpperCase()} ok={status.backend.status === 'online'} sub={`${status.backend.latency_ms}ms`} />
        <StatusCard label="Feed Candles" value={status.feed.status.toUpperCase()} ok={status.feed.status === 'online'} sub={`${status.feed.candles_per_min}/min`} />
        <StatusCard label="Latência" value={`${status.simulated_latency_ms}ms`} sub="simulada" />
        <StatusCard label="Ordens Abertas" value={status.open_orders} ok={status.open_orders < 5} />
      </div>

      {/* Detail row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <StatusCard label="Último Ciclo" value={new Date(status.fusion.last_cycle).toLocaleTimeString('pt-BR')} sub="Fusion" />
        <StatusCard label="Duração Ciclo" value={`${status.fusion.cycle_duration_ms}ms`} ok={status.fusion.cycle_duration_ms < 500} />
        <StatusCard label="Ativos Mon." value={status.symbols_monitored.join(', ')} />
        <StatusCard label="Timeframes Mon." value={status.timeframes_monitored.join(', ')} />
        <StatusCard label="Último Sinal" value={`${status.last_signal.direction} ${status.last_signal.symbol}`} sub={new Date(status.last_signal.ts).toLocaleTimeString('pt-BR')} />
        <StatusCard label="Última Ordem" value={`#${status.last_order.ticket} ${status.last_order.symbol}`} sub={new Date(status.last_order.ts).toLocaleTimeString('pt-BR')} />
        <StatusCard label="Último Erro" value={status.last_critical_error || 'Nenhum'} ok={!status.last_critical_error} />
        <StatusCard label="Alertas Ativos" value={unacked.length} ok={unacked.length === 0} />
      </div>

      {/* Active Alerts */}
      {unacked.length > 0 && (
        <div className="bg-card border border-border rounded p-3">
          <div className="text-xs font-bold text-red-400 mb-2 uppercase">Alertas Ativos</div>
          <div className="space-y-1">
            {unacked.map(a => (
              <div key={a.id} className={cn('flex items-center gap-2 text-xs py-1 border-b border-border last:border-0',
                a.severity === 'error' ? 'text-red-400' : 'text-yellow-400')}>
                <AlertTriangle size={10} />
                <span className="font-mono">{new Date(a.timestamp).toLocaleTimeString('pt-BR')}</span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
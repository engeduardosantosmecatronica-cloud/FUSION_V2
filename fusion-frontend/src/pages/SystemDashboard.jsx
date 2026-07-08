import { useEffect, useState } from 'react';
import { getSystemStatus, getAlerts } from '@/services/api';
import { cn } from '@/lib/utils';
import { AlertTriangle } from 'lucide-react';

function StatusCard({ label, value, ok, sub }) {
  return (
    <div className="bg-card border border-border rounded p-3 flex flex-col gap-1">
      <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className={cn('text-sm font-bold break-words', ok === true ? 'text-green-400' : ok === false ? 'text-red-400' : 'text-foreground')}>
        {value ?? '-'}
      </span>
      {sub ? <span className="text-xs text-muted-foreground break-words">{sub}</span> : null}
    </div>
  );
}

function safeTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleTimeString('pt-BR');
}

export default function SystemDashboard() {
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    let mounted = true;
    const load = () => {
      getSystemStatus().then((data) => mounted && setStatus(data)).catch(() => {});
      getAlerts().then((data) => mounted && setAlerts(Array.isArray(data) ? data : [])).catch(() => {});
    };
    load();
    const id = setInterval(load, 8000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  if (!status) return <div className="text-muted-foreground text-sm p-8">Carregando...</div>;

  const fusion = status.fusion || {};
  const mt5 = status.mt5 || {};
  const backend = status.backend || {};
  const feed = status.feed || {};
  const symbols = Array.isArray(status.symbols_monitored) ? status.symbols_monitored : [];
  const timeframes = Array.isArray(status.timeframes_monitored) ? status.timeframes_monitored : [];
  const lastSignal = status.last_signal || null;
  const lastOrder = status.last_order || null;
  const openOrders = Number(status.open_orders || 0);
  const unacked = (Array.isArray(alerts) ? alerts : []).filter(a => !a.acknowledged);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Dashboard do Sistema</h1>
        <span className="text-xs text-green-400 flex items-center gap-1">API REAL</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
        <StatusCard label="Fusion" value={(fusion.status || 'offline').toUpperCase()} ok={fusion.status === 'online'} sub={`Ciclo: ${fusion.cycle_duration_ms ?? '-'}ms`} />
        <StatusCard label="MT5" value={(mt5.status || 'offline').toUpperCase()} ok={mt5.status === 'online'} sub={mt5.account || mt5.server || 'MT5 direto'} />
        <StatusCard label="Backend/API" value={(backend.status || 'offline').toUpperCase()} ok={backend.status === 'online'} sub={`${backend.latency_ms ?? 0}ms`} />
        <StatusCard label="Feed Candles" value={(feed.status || 'offline').toUpperCase()} ok={feed.status === 'online'} sub={`${feed.candles_per_min ?? 0}/min`} />
        <StatusCard label="Latencia" value={`${status.simulated_latency_ms ?? 0}ms`} sub="API local" />
        <StatusCard label="Ordens Abertas" value={openOrders} ok={openOrders < 5} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <StatusCard label="Ultimo Ciclo" value={safeTime(fusion.last_cycle)} sub="Fusion" />
        <StatusCard label="Duracao Ciclo" value={`${fusion.cycle_duration_ms ?? '-'}ms`} ok={(fusion.cycle_duration_ms ?? 999999) < 5000} />
        <StatusCard label="Ativos Mon." value={symbols.length ? symbols.join(', ') : 'Aguardando ciclo'} />
        <StatusCard label="Timeframes Mon." value={timeframes.length ? timeframes.join(', ') : '-'} />
        <StatusCard label="Ultimo Sinal" value={lastSignal ? `${lastSignal.direction} ${lastSignal.symbol}` : 'Sem sinal'} sub={safeTime(lastSignal?.ts)} />
        <StatusCard label="Ultima Ordem" value={lastOrder ? `#${lastOrder.ticket} ${lastOrder.symbol}` : 'Nenhuma'} sub={safeTime(lastOrder?.opened_at || lastOrder?.ts)} />
        <StatusCard label="Ultimo Erro" value={status.last_critical_error || 'Nenhum'} ok={!status.last_critical_error} />
        <StatusCard label="Alertas Ativos" value={unacked.length} ok={unacked.length === 0} />
      </div>

      {unacked.length > 0 && (
        <div className="bg-card border border-border rounded p-3">
          <div className="text-xs font-bold text-red-400 mb-2 uppercase">Alertas Ativos</div>
          <div className="space-y-1">
            {unacked.map(a => (
              <div key={a.id} className={cn('flex items-center gap-2 text-xs py-1 border-b border-border last:border-0',
                a.severity === 'error' ? 'text-red-400' : 'text-yellow-400')}>
                <AlertTriangle size={10} />
                <span className="font-mono">{safeTime(a.timestamp)}</span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


import { useEffect, useState } from 'react';
import { getAlerts, acknowledgeAlert } from '@/services/api';
import { cn } from '@/lib/utils';
import { AlertTriangle, CheckCircle, Bell } from 'lucide-react';

const TYPE_LABELS = {
  mt5_disconnected: 'MT5 Desconectado',
  backend_offline: 'Backend Offline',
  fusion_no_cycle: 'Fusion sem ciclo',
  no_candle: 'Sem candles recentes',
  order_rejected: 'Ordem rejeitada',
  spread_high: 'Spread alto',
  model_missing: 'Modelo ausente',
  critical_error: 'Erro crítico',
  autotrading_off: 'AutoTrading OFF',
};

const SEV_COLOR = { error: 'border-red-700 bg-red-950/30', warning: 'border-yellow-700 bg-yellow-950/30' };
const SEV_ICON = { error: 'text-red-400', warning: 'text-yellow-400' };

export default function Alertas() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => getAlerts().then(a => { setAlerts(a); setLoading(false); });
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, []);

  const ack = async (id) => {
    await acknowledgeAlert(id);
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
  };

  const active = alerts.filter(a => !a.acknowledged);
  const done = alerts.filter(a => a.acknowledged);

  if (loading) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Central de Alertas</h1>
        <span className={cn('text-xs px-2 py-0.5 rounded font-bold', active.length > 0 ? 'bg-red-900 text-red-300' : 'bg-secondary text-muted-foreground')}>
          {active.length} ativos
        </span>
      </div>

      {/* Active */}
      <div className="space-y-2">
        <div className="text-xs text-muted-foreground uppercase font-bold">Ativos</div>
        {active.length === 0 && (
          <div className="flex items-center gap-2 text-xs text-green-400 border border-green-800 rounded p-3">
            <CheckCircle size={12} /> Nenhum alerta ativo
          </div>
        )}
        {active.map(a => (
          <div key={a.id} className={cn('flex items-center gap-3 border rounded p-3 text-xs', SEV_COLOR[a.severity])}>
            <AlertTriangle size={14} className={SEV_ICON[a.severity]} />
            <div className="flex-1">
              <div className="font-bold text-foreground">{TYPE_LABELS[a.type] || a.type}</div>
              <div className="text-muted-foreground mt-0.5">{a.message}</div>
              <div className="text-muted-foreground mt-0.5">{new Date(a.timestamp).toLocaleString('pt-BR')}</div>
            </div>
            <button onClick={() => ack(a.id)}
              className="text-xs px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent whitespace-nowrap">
              Confirmar
            </button>
          </div>
        ))}
      </div>

      {/* Acknowledged */}
      {done.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground uppercase font-bold">Reconhecidos</div>
          {done.map(a => (
            <div key={a.id} className="flex items-center gap-3 border border-border rounded p-3 text-xs opacity-50">
              <CheckCircle size={14} className="text-green-400" />
              <div className="flex-1">
                <div className="font-medium">{TYPE_LABELS[a.type] || a.type}</div>
                <div className="text-muted-foreground">{a.message}</div>
              </div>
              <span className="text-muted-foreground">{new Date(a.timestamp).toLocaleString('pt-BR')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
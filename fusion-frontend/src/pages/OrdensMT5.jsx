import { useEffect, useState } from 'react';
import { getOpenOrders, closeOrder, updateOrder } from '@/services/api';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

function OrderModal({ order, onClose, onAction }) {
  const [action, setAction] = useState('close'); // close | partial | sl | tp | trailing
  const [val, setVal] = useState('');
  const [msg, setMsg] = useState('');

  const submit = async () => {
    let res;
    if (action === 'close') res = await closeOrder(order.ticket);
    else if (action === 'partial') res = await closeOrder(order.ticket, true, parseFloat(val));
    else res = await updateOrder(order.ticket, { [action === 'sl' ? 'sl' : action === 'tp' ? 'tp' : 'trailing_active']: action === 'trailing' ? val === 'on' : parseFloat(val) });
    setMsg(res.message || 'OK');
    setTimeout(() => { onClose(); onAction(); }, 1500);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-card border border-border rounded p-4 w-80" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-primary">#{order.ticket} {order.symbol} {order.direction}</span>
          <button onClick={onClose}><X size={14} /></button>
        </div>
        <div className="space-y-2">
          <select value={action} onChange={e => setAction(e.target.value)}
            className="w-full bg-secondary border border-border rounded px-2 py-1.5 text-xs">
            <option value="close">Fechar Ordem</option>
            <option value="partial">Fechamento Parcial</option>
            <option value="sl">Mover SL</option>
            <option value="tp">Alterar TP</option>
            <option value="trailing">Trailing ON/OFF</option>
          </select>
          {action !== 'close' && action !== 'trailing' && (
            <input type="number" step="0.00001" placeholder={action === 'partial' ? 'Lots' : 'PreÃ§o'}
              value={val} onChange={e => setVal(e.target.value)}
              className="w-full bg-secondary border border-border rounded px-2 py-1.5 text-xs" />
          )}
          {action === 'trailing' && (
            <select value={val} onChange={e => setVal(e.target.value)}
              className="w-full bg-secondary border border-border rounded px-2 py-1.5 text-xs">
              <option value="on">Ativar Trailing</option>
              <option value="off">Desativar Trailing</option>
            </select>
          )}
          {msg ? <div className="text-xs text-green-400 font-medium">{msg}</div> : (
            <button onClick={submit} className="w-full text-xs py-2 bg-primary text-primary-foreground rounded">Executar no MT5</button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OrdensMT5() {
  const [orders, setOrders] = useState([]);
  const [selected, setSelected] = useState(null);

  const load = () => getOpenOrders().then((data) => setOrders(Array.isArray(data) ? data : []));
  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-3">
      {selected && <OrderModal order={selected} onClose={() => setSelected(null)} onAction={load} />}
      <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Ordens MT5</h1>
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Ticket','SÃ­mbolo','Dir','Lots','Entrada','Atual','SL','TP','P/L','Magic','EstratÃ©gia','TF','Abertura','Trail','AÃ§Ã£o'].map(h => (
                <th key={h} className="px-2 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {orders.map(o => (
              <tr key={o.ticket} className="border-b border-border hover:bg-accent">
                <td className="px-2 py-1.5 font-mono">{o.ticket}</td>
                <td className="px-2 py-1.5 font-bold">{o.symbol}</td>
                <td className={cn('px-2 py-1.5 font-bold', o.direction === 'BUY' ? 'text-green-400' : 'text-red-400')}>{o.direction}</td>
                <td className="px-2 py-1.5 font-mono">{o.lots}</td>
                <td className="px-2 py-1.5 font-mono">{o.entry_price}</td>
                <td className="px-2 py-1.5 font-mono">{o.current_price}</td>
                <td className="px-2 py-1.5 font-mono text-red-400">{o.sl}</td>
                <td className="px-2 py-1.5 font-mono text-green-400">{o.tp}</td>
                <td className={cn('px-2 py-1.5 font-mono font-bold', o.profit >= 0 ? 'text-green-400' : 'text-red-400')}>
                  {o.profit >= 0 ? '+' : ''}{o.profit.toFixed(2)}
                </td>
                <td className="px-2 py-1.5 font-mono text-muted-foreground">{o.magic_number}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{o.strategy}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{o.timeframe}</td>
                <td className="px-2 py-1.5 font-mono text-muted-foreground">{new Date(o.opened_at).toLocaleTimeString('pt-BR')}</td>
                <td className={cn('px-2 py-1.5 font-medium', o.trailing_active ? 'text-green-400' : 'text-muted-foreground')}>
                  {o.trailing_active ? 'ON' : 'OFF'}
                </td>
                <td className="px-2 py-1.5">
                  <button onClick={() => setSelected(o)} className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded hover:bg-primary/40">
                    AÃ§Ãµes
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {orders.length === 0 && <div className="text-center text-muted-foreground text-xs py-8">Nenhuma ordem aberta</div>}
      </div>
    </div>
  );
}

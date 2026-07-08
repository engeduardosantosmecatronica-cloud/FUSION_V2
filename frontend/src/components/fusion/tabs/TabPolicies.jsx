import { useState } from 'react';
import { Field, NumInput, ChipListEditor, Section } from '../FusionFieldRenderers';
import { cn } from '@/lib/utils';

const TIMEFRAMES = ['default', 'M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'];
const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'GBPJPY', 'AUDCAD', 'USDCAD', 'AUDNZD', 'EURGBP', 'EURJPY', 'AUDCHF', 'NZDSGD', 'EURAUD', 'EURNZD'];
const ALL_FILTERS = ['market_alignment', 'timeframe_consensus', 'session_context', 'market_regime', 'volatility_engine', 'macro_flow', 'portfolio_correlation', 'risk_engine', 'ema_alignment', 'entry_timing', 'execution_engine', 'context_engine'];

export default function TabPolicies({ draft, set }) {
  const policies = draft.runtime?.symbol_timeframe_policies || {};
  const [newSym, setNewSym] = useState('EURUSD');
  const [newTf, setNewTf] = useState('default');

  const updatePolicy = (key, path, value) => {
    const current = policies[key] || { signals: {}, filters: { required_filters: [], soft_filters: [] } };
    const parts = path.split('.');
    let updated = { ...current };
    if (parts.length === 2) {
      updated[parts[0]] = { ...(updated[parts[0]] || {}), [parts[1]]: value };
    } else {
      updated[path] = value;
    }
    set('runtime', { ...draft.runtime, symbol_timeframe_policies: { ...policies, [key]: updated } });
  };

  const addPolicy = () => {
    const key = `${newSym}.${newTf}`;
    if (!policies[key]) {
      set('runtime', {
        ...draft.runtime,
        symbol_timeframe_policies: {
          ...policies,
          [key]: { signals: { buy_threshold: 0.55, sell_threshold: 0.55, confidence_filter: 0.60, min_signal_strength: 0.50 }, filters: { required_filters: [], soft_filters: [] } },
        },
      });
    }
  };

  const removePolicy = (key) => {
    const updated = { ...policies };
    delete updated[key];
    set('runtime', { ...draft.runtime, symbol_timeframe_policies: updated });
  };

  return (
    <div className="space-y-2">
      {/* Add policy */}
      <div className="flex items-center gap-2 border border-border rounded px-3 py-2 bg-card">
        <span className="text-xs text-muted-foreground">Adicionar política:</span>
        <select value={newSym} onChange={e => setNewSym(e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
          {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={newTf} onChange={e => setNewTf(e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
          {TIMEFRAMES.map(tf => <option key={tf} value={tf}>{tf}</option>)}
        </select>
        <button onClick={addPolicy} className="text-xs px-3 py-1 bg-primary/20 text-primary rounded hover:bg-primary/30">+ Adicionar</button>
      </div>

      {/* Policy table */}
      <div className="overflow-x-auto border border-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary text-muted-foreground">
              {['Chave', 'BUY Thr.', 'SELL Thr.', 'Conf. Filter', 'Min Strength', 'Required Filters', 'Soft Filters', ''].map(h => (
                <th key={h} className="px-2 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(policies).map(([key, pol]) => (
              <tr key={key} className="border-b border-border hover:bg-accent align-top">
                <td className="px-2 py-1.5 font-mono font-bold text-primary whitespace-nowrap">{key}</td>
                <td className="px-2 py-1.5">
                  <input type="number" step="0.01" min="0" max="1" value={pol.signals?.buy_threshold ?? 0.55}
                    onChange={e => updatePolicy(key, 'signals.buy_threshold', parseFloat(e.target.value))}
                    className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-16 text-right font-mono" />
                </td>
                <td className="px-2 py-1.5">
                  <input type="number" step="0.01" min="0" max="1" value={pol.signals?.sell_threshold ?? 0.55}
                    onChange={e => updatePolicy(key, 'signals.sell_threshold', parseFloat(e.target.value))}
                    className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-16 text-right font-mono" />
                </td>
                <td className="px-2 py-1.5">
                  <input type="number" step="0.01" min="0" max="1" value={pol.signals?.confidence_filter ?? 0.60}
                    onChange={e => updatePolicy(key, 'signals.confidence_filter', parseFloat(e.target.value))}
                    className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-16 text-right font-mono" />
                </td>
                <td className="px-2 py-1.5">
                  <input type="number" step="0.01" min="0" max="1" value={pol.signals?.min_signal_strength ?? 0.50}
                    onChange={e => updatePolicy(key, 'signals.min_signal_strength', parseFloat(e.target.value))}
                    className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-16 text-right font-mono" />
                </td>
                <td className="px-2 py-1.5 max-w-32">
                  <div className="flex flex-wrap gap-0.5">
                    {(pol.filters?.required_filters || []).map(f => (
                      <span key={f} className="text-xs px-1 bg-primary/20 text-primary rounded">{f}</span>
                    ))}
                  </div>
                </td>
                <td className="px-2 py-1.5 max-w-32">
                  <div className="flex flex-wrap gap-0.5">
                    {(pol.filters?.soft_filters || []).map(f => (
                      <span key={f} className="text-xs px-1 bg-yellow-900/40 text-yellow-400 rounded">{f}</span>
                    ))}
                  </div>
                </td>
                <td className="px-2 py-1.5">
                  <button onClick={() => removePolicy(key)} className="text-xs text-red-400 hover:text-red-300">×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
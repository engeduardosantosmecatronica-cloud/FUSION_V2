import { useState } from 'react';
import { Field, Toggle, ChipListEditor, ModeSelect, Section } from '../FusionFieldRenderers';

const ASSET_TYPES = ['forex', 'commodity', 'index', 'crypto', 'stock'];

export default function TabContratos({ draft, set }) {
  const contracts = draft.contracts || { overrides: [] };
  const rtSym = draft.runtime?.symbols || { mode: 'include', include: [], exclude: [] };
  const [newSym, setNewSym] = useState('');
  const [newBroker, setNewBroker] = useState('');
  const [newType, setNewType] = useState('forex');

  const updRTSym = (k, v) => set('runtime', { ...draft.runtime, symbols: { ...rtSym, [k]: v } });

  const addOverride = () => {
    if (newSym.trim()) {
      set('contracts', { ...contracts, overrides: [...(contracts.overrides || []), { symbol: newSym.trim(), broker_symbol: newBroker.trim() || newSym.trim(), asset_type: newType }] });
      setNewSym(''); setNewBroker('');
    }
  };

  const removeOverride = (i) => {
    const ovs = [...(contracts.overrides || [])];
    ovs.splice(i, 1);
    set('contracts', { ...contracts, overrides: ovs });
  };

  const updateOverride = (i, k, v) => {
    const ovs = [...(contracts.overrides || [])];
    ovs[i] = { ...ovs[i], [k]: v };
    set('contracts', { ...contracts, overrides: ovs });
  };

  return (
    <div className="space-y-2">
      <Section title="Contratos — Symbol Overrides">
        <div className="overflow-x-auto">
          <table className="w-full text-xs mb-2">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="px-2 py-1.5 text-left">Símbolo</th>
                <th className="px-2 py-1.5 text-left">Broker Symbol</th>
                <th className="px-2 py-1.5 text-left">Asset Type</th>
                <th className="px-2 py-1.5"></th>
              </tr>
            </thead>
            <tbody>
              {(contracts.overrides || []).map((ov, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="px-2 py-1"><input value={ov.symbol} onChange={e => updateOverride(i, 'symbol', e.target.value)} className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-24 font-mono" /></td>
                  <td className="px-2 py-1"><input value={ov.broker_symbol} onChange={e => updateOverride(i, 'broker_symbol', e.target.value)} className="bg-secondary border border-border rounded px-1 py-0.5 text-xs w-24 font-mono" /></td>
                  <td className="px-2 py-1">
                    <select value={ov.asset_type} onChange={e => updateOverride(i, 'asset_type', e.target.value)} className="bg-secondary border border-border rounded px-1 py-0.5 text-xs">
                      {ASSET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td className="px-2 py-1"><button onClick={() => removeOverride(i)} className="text-xs text-red-400">×</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex gap-2">
            <input value={newSym} onChange={e => setNewSym(e.target.value)} placeholder="Símbolo" className="bg-secondary border border-border rounded px-2 py-1 text-xs w-24" />
            <input value={newBroker} onChange={e => setNewBroker(e.target.value)} placeholder="Broker" className="bg-secondary border border-border rounded px-2 py-1 text-xs w-24" />
            <select value={newType} onChange={e => setNewType(e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
              {ASSET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={addOverride} className="text-xs px-2 py-1 bg-primary/20 text-primary rounded">+</button>
          </div>
        </div>
      </Section>

      <Section title="Símbolos (global)">
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">symbols</div><ChipListEditor value={draft.symbols || []} onChange={v => set('symbols', v)} /></div>
      </Section>

      <Section title="Runtime Symbols" defaultOpen={false}>
        <Field label="mode">
          <select value={rtSym.mode || 'include'} onChange={e => updRTSym('mode', e.target.value)} className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            <option value="include">include</option>
            <option value="exclude">exclude</option>
          </select>
        </Field>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">include</div><ChipListEditor value={rtSym.include || []} onChange={v => updRTSym('include', v)} /></div>
        <div className="py-1"><div className="text-xs text-muted-foreground mb-1">exclude</div><ChipListEditor value={rtSym.exclude || []} onChange={v => updRTSym('exclude', v)} /></div>
      </Section>
    </div>
  );
}
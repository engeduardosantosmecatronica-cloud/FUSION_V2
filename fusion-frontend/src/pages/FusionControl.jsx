import { useEffect, useState, useCallback } from 'react';
import { getFusionRuntimeControl, updateFusionRuntimeControl, getFusionConfigDiff, exportFusionRuntimeControl, importFusionRuntimeControl, applyFusionPreset } from '@/services/fusionRuntimeApi';
import { cn } from '@/lib/utils';
import FusionDraftBar from '@/components/fusion/FusionDraftBar';
import FusionDiffViewer from '@/components/fusion/FusionDiffViewer';
import FusionPresetBar from '@/components/fusion/FusionPresetBar';

import TabGeral from '@/components/fusion/tabs/TabGeral';
import TabBroker from '@/components/fusion/tabs/TabBroker';
import TabTrading from '@/components/fusion/tabs/TabTrading';
import TabRisco from '@/components/fusion/tabs/TabRisco';
import TabSinais from '@/components/fusion/tabs/TabSinais';
import TabPolicies from '@/components/fusion/tabs/TabPolicies';
import TabFiltros from '@/components/fusion/tabs/TabFiltros';
import TabStrategies from '@/components/fusion/tabs/TabStrategies';
import TabTrailing from '@/components/fusion/tabs/TabTrailing';
import TabDashboardLogs from '@/components/fusion/tabs/TabDashboardLogs';
import TabCurrencyStrength from '@/components/fusion/tabs/TabCurrencyStrength';
import TabOTM from '@/components/fusion/tabs/TabOTM';
import TabModelos from '@/components/fusion/tabs/TabModelos';
import TabMT5Panels from '@/components/fusion/tabs/TabMT5Panels';
import TabSignalOverrides from '@/components/fusion/tabs/TabSignalOverrides';
import TabContratos from '@/components/fusion/tabs/TabContratos';
import TabOMS from '@/components/fusion/tabs/TabOMS';
import TabJsonEditor from '@/components/fusion/tabs/TabJsonEditor';

const TABS = [
  { id: 'geral', label: 'Geral' },
  { id: 'broker', label: 'Broker/MT5' },
  { id: 'trading', label: 'Trading' },
  { id: 'risco', label: 'Risco' },
  { id: 'sinais', label: 'Sinais' },
  { id: 'policies', label: 'Políticas' },
  { id: 'filtros', label: 'Filtros' },
  { id: 'strategies', label: 'Estratégias' },
  { id: 'trailing', label: 'Trailing/TP/SL' },
  { id: 'dashboard', label: 'Dashboard/Logs' },
  { id: 'currency', label: 'Currency Str.' },
  { id: 'otm', label: 'OTM' },
  { id: 'modelos', label: 'Modelos/IA' },
  { id: 'mt5panels', label: 'MT5 Panels' },
  { id: 'overrides', label: 'Overrides' },
  { id: 'contratos', label: 'Contratos' },
  { id: 'oms', label: 'OMS' },
  { id: 'json', label: 'JSON Avançado' },
];

function setDeep(obj, path, value) {
  const keys = path.split('.');
  const result = { ...obj };
  let cur = result;
  for (let i = 0; i < keys.length - 1; i++) {
    cur[keys[i]] = { ...cur[keys[i]] };
    cur = cur[keys[i]];
  }
  cur[keys[keys.length - 1]] = value;
  return result;
}

export default function FusionControl() {
  const [original, setOriginal] = useState(null);
  const [draft, setDraft] = useState(null);
  const [diff, setDiff] = useState([]);
  const [tab, setTab] = useState('geral');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getFusionRuntimeControl().then(c => { setOriginal(c); setDraft(c); });
  }, []);

  useEffect(() => {
    if (original && draft) {
      getFusionConfigDiff(original, draft).then(setDiff);
    }
  }, [draft, original]);

  const set = useCallback((key, value) => {
    setDraft(d => ({ ...d, [key]: value }));
  }, []);

  const save = async () => {
    setSaving(true);
    setError('');
    await updateFusionRuntimeControl(draft);
    setOriginal(draft);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const discard = () => { setDraft(original); };

  const handleExport = async () => {
    const json = await exportFusionRuntimeControl();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'fusion_runtime_control.json'; a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const imported = await importFusionRuntimeControl(text);
    setDraft(imported);
  };

  const handlePreset = async (name) => {
    const patches = await applyFusionPreset(name);
    let updated = { ...draft };
    Object.entries(patches).forEach(([path, value]) => {
      updated = setDeep(updated, path, value);
    });
    setDraft(updated);
  };

  const applyJson = (parsed) => { setDraft(parsed); };

  if (!draft) return <div className="text-muted-foreground text-sm">Carregando configuração Fusion...</div>;

  const hasDiff = diff.length > 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div>
          <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Fusion Control Center</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Configuração completa do Fusion — edição em modo draft com diff antes de aplicar</p>
        </div>
      </div>

      <FusionPresetBar onApply={handlePreset} />
      <FusionDraftBar hasDiff={hasDiff} diffCount={diff.length} onSave={save} onDiscard={discard} onExport={handleExport} onImport={handleImport} saving={saving} saved={saved} error={error} />
      {hasDiff && <FusionDiffViewer diff={diff} />}

      {/* Tab bar */}
      <div className="flex flex-wrap gap-0 border-b border-border mb-4 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'px-3 py-2 text-xs font-medium border-b-2 whitespace-nowrap transition-colors',
              tab === t.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'geral' && <TabGeral draft={draft} set={set} />}
        {tab === 'broker' && <TabBroker draft={draft} set={set} />}
        {tab === 'trading' && <TabTrading draft={draft} set={set} />}
        {tab === 'risco' && <TabRisco draft={draft} set={set} />}
        {tab === 'sinais' && <TabSinais draft={draft} set={set} />}
        {tab === 'policies' && <TabPolicies draft={draft} set={set} />}
        {tab === 'filtros' && <TabFiltros draft={draft} set={set} />}
        {tab === 'strategies' && <TabStrategies draft={draft} set={set} />}
        {tab === 'trailing' && <TabTrailing draft={draft} set={set} />}
        {tab === 'dashboard' && <TabDashboardLogs draft={draft} set={set} />}
        {tab === 'currency' && <TabCurrencyStrength draft={draft} set={set} />}
        {tab === 'otm' && <TabOTM draft={draft} set={set} />}
        {tab === 'modelos' && <TabModelos draft={draft} set={set} />}
        {tab === 'mt5panels' && <TabMT5Panels draft={draft} set={set} />}
        {tab === 'overrides' && <TabSignalOverrides draft={draft} set={set} />}
        {tab === 'contratos' && <TabContratos draft={draft} set={set} />}
        {tab === 'oms' && <TabOMS draft={draft} set={set} />}
        {tab === 'json' && <TabJsonEditor draft={draft} original={original} onApply={applyJson} />}
      </div>
    </div>
  );
}
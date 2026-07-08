import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMarketBriefing, updateMarketBriefing } from '@/services/api';
import { cn } from '@/lib/utils';

const CURRENCY_BIAS_OPTIONS = ['bullish', 'neutral_bullish', 'neutral', 'neutral_bearish', 'bearish'];
const PAIR_BIAS_OPTIONS = ['BUY', 'neutral_buy', 'neutral', 'neutral_sell', 'SELL'];
const RISK_OPTIONS = [
  'event_driven_relief_range_fx_high_jpy_carry',
  'event_driven_range_fx',
  'risk_on',
  'risk_off',
  'neutral',
  'high_volatility',
];

const BIAS_COLOR = {
  bullish: 'text-green-400',
  neutral_bullish: 'text-emerald-300',
  BUY: 'text-green-400',
  neutral_buy: 'text-emerald-300',
  bearish: 'text-red-400',
  neutral_bearish: 'text-rose-300',
  SELL: 'text-red-400',
  neutral_sell: 'text-rose-300',
  neutral: 'text-muted-foreground',
};

function normalizeBriefing(payload) {
  const data = payload && typeof payload === 'object' ? payload : {};
  return {
    enabled: data.enabled ?? true,
    date: data.date || '',
    valid_until: data.valid_until || '',
    summary: data.summary || '',
    risk_regime: data.risk_regime || '',
    notes: Array.isArray(data.notes) ? data.notes : [],
    market_snapshot: data.market_snapshot && typeof data.market_snapshot === 'object' ? data.market_snapshot : {},
    currency_bias: data.currency_bias && typeof data.currency_bias === 'object' ? data.currency_bias : {},
    pair_bias: data.pair_bias && typeof data.pair_bias === 'object' ? data.pair_bias : {},
    asset_bias: data.asset_bias && typeof data.asset_bias === 'object' ? data.asset_bias : {},
    rules: Array.isArray(data.rules) ? data.rules : Array.isArray(data.macro_rules) ? data.macro_rules : [],
    is_expired: !!data.is_expired,
    last_updated: data.last_updated || data.date || '',
  };
}

function makeSignature(data) {
  if (!data) return '';
  const clean = { ...data };
  delete clean.is_expired;
  delete clean.last_updated;
  return JSON.stringify(clean);
}

function getBiasValue(value) {
  if (value && typeof value === 'object') return value.bias || 'neutral';
  return value || 'neutral';
}

function getStrengthValue(value) {
  if (value && typeof value === 'object') return Number(value.strength ?? 0.5);
  return 0.5;
}

function setBiasEntry(current, nextBias) {
  if (current && typeof current === 'object') return { ...current, bias: nextBias };
  return nextBias;
}

function setStrengthEntry(current, nextStrength) {
  const strength = Number(nextStrength);
  if (current && typeof current === 'object') return { ...current, strength };
  return { bias: current || 'neutral', strength };
}

function SelectField({ value, options, onChange }) {
  return (
    <select
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      className={cn('bg-secondary border border-border rounded px-2 py-1 text-xs min-w-0', BIAS_COLOR[value])}
    >
      {!options.includes(value) && value ? <option value={value}>{value}</option> : null}
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

function BiasGrid({ title, data, options, onChange, onStrengthChange }) {
  const entries = Object.entries(data || {});
  return (
    <div>
      <div className="text-xs text-muted-foreground uppercase mb-2">{title}</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {entries.map(([key, value]) => {
          const bias = getBiasValue(value);
          const strength = getStrengthValue(value);
          return (
            <div key={key} className="flex items-center gap-2 rounded border border-border bg-secondary/30 px-2 py-1.5 min-w-0">
              <span className="text-xs font-bold font-mono w-16 shrink-0 truncate" title={key}>{key}</span>
              <SelectField value={bias} options={options} onChange={v => onChange(key, v)} />
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={Number.isFinite(strength) ? strength : 0.5}
                onChange={e => onStrengthChange(key, e.target.value)}
                className="w-16 bg-secondary border border-border rounded px-1 py-1 text-xs font-mono text-right"
                title="strength"
              />
            </div>
          );
        })}
      </div>
      {entries.length === 0 && <div className="text-xs text-muted-foreground">Sem dados nesta seção.</div>}
    </div>
  );
}

function RuleEditor({ rules, setRules }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground uppercase mb-2">Regras Macro</div>
      <div className="space-y-2">
        {(rules || []).map((rule, i) => {
          if (typeof rule === 'string') {
            return (
              <input
                key={i}
                value={rule}
                onChange={e => {
                  const next = [...rules];
                  next[i] = e.target.value;
                  setRules(next);
                }}
                className="w-full bg-secondary border border-border rounded px-2 py-1 text-xs"
              />
            );
          }
          const item = rule && typeof rule === 'object' ? rule : {};
          return (
            <div key={i} className="rounded border border-border bg-secondary/30 p-2 space-y-2">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <input
                  value={item.label || ''}
                  onChange={e => {
                    const next = [...rules];
                    next[i] = { ...item, label: e.target.value };
                    setRules(next);
                  }}
                  placeholder="label"
                  className="bg-secondary border border-border rounded px-2 py-1 text-xs"
                />
                <select
                  value={item.risk || 'MEDIO'}
                  onChange={e => {
                    const next = [...rules];
                    next[i] = { ...item, risk: e.target.value };
                    setRules(next);
                  }}
                  className="bg-secondary border border-border rounded px-2 py-1 text-xs"
                >
                  {['BAIXO', 'MEDIO', 'ALTO'].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
                <select
                  value={item.action || 'monitor'}
                  onChange={e => {
                    const next = [...rules];
                    next[i] = { ...item, action: e.target.value };
                    setRules(next);
                  }}
                  className="bg-secondary border border-border rounded px-2 py-1 text-xs"
                >
                  {['monitor', 'moderate', 'reduce_exposure', 'block'].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div className="text-[10px] text-muted-foreground truncate" title={(item.symbols || []).join(', ')}>
                {(item.symbols || []).join(', ') || 'sem símbolos'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function MarketBriefing() {
  const [briefing, setBriefing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [lastAppliedSignature, setLastAppliedSignature] = useState('');

  const { data: remoteBriefing, isFetching, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['market-briefing'],
    queryFn: async () => normalizeBriefing(await getMarketBriefing()),
    staleTime: 0,
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    if (!remoteBriefing) return;
    const signature = makeSignature(remoteBriefing);
    if (!dirty || signature !== lastAppliedSignature) {
      setBriefing(remoteBriefing);
      setLastAppliedSignature(signature);
      setDirty(false);
    }
  }, [remoteBriefing, dirty, lastAppliedSignature]);

  const markUpdate = (updater) => {
    setBriefing(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      return normalizeBriefing(next);
    });
    setDirty(true);
  };

  const save = async () => {
    setSaving(true);
    const payload = { ...briefing, macro_rules: undefined, is_expired: undefined, last_updated: undefined };
    delete payload.macro_rules;
    delete payload.is_expired;
    delete payload.last_updated;
    await updateMarketBriefing(payload);
    setSaving(false);
    setSaved(true);
    setDirty(false);
    await refetch();
    setTimeout(() => setSaved(false), 2000);
  };

  const syncedAt = useMemo(() => dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString('pt-BR') : '--:--:--', [dataUpdatedAt]);

  if (!briefing) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  const expired = briefing.is_expired;

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Market Briefing</h1>
          <p className="text-xs text-muted-foreground">Atualiza automaticamente a cada 5s a partir de config/market_briefing_today.json</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {expired && <span className="text-red-400 flex items-center gap-1 border border-red-700 rounded px-2 py-1">! Briefing vencido</span>}
          {dirty && <span className="text-yellow-400 border border-yellow-700 rounded px-2 py-1">edição local</span>}
          <span className={cn('border rounded px-2 py-1', isFetching ? 'text-blue-400 border-blue-700' : 'text-green-400 border-green-700')}>
            {isFetching ? 'sincronizando...' : `sincronizado ${syncedAt}`}
          </span>
          <button onClick={() => refetch()} className="px-2 py-1 rounded border border-border hover:bg-secondary">Atualizar</button>
        </div>
      </div>

      <div className="bg-card border border-border rounded p-4 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_260px] gap-4">
          <div>
            <label className="text-xs text-muted-foreground uppercase">Resumo do Dia</label>
            <textarea
              value={briefing.summary}
              onChange={e => markUpdate(b => ({ ...b, summary: e.target.value }))}
              rows={7}
              className="mt-1 w-full bg-secondary border border-border rounded px-3 py-2 text-xs resize-none"
            />
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground uppercase">Data</label>
              <input value={briefing.date} onChange={e => markUpdate(b => ({ ...b, date: e.target.value }))} className="mt-1 w-full bg-secondary border border-border rounded px-2 py-1 text-xs" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground uppercase">Validade</label>
              <input value={briefing.valid_until} onChange={e => markUpdate(b => ({ ...b, valid_until: e.target.value }))} className="mt-1 w-full bg-secondary border border-border rounded px-2 py-1 text-xs" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground uppercase">Risk Regime</label>
              <select
                value={briefing.risk_regime}
                onChange={e => markUpdate(b => ({ ...b, risk_regime: e.target.value }))}
                className="mt-1 w-full bg-secondary border border-border rounded px-2 py-1 text-xs"
              >
                {!RISK_OPTIONS.includes(briefing.risk_regime) && briefing.risk_regime ? <option value={briefing.risk_regime}>{briefing.risk_regime}</option> : null}
                {RISK_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>
        </div>

        <BiasGrid
          title="Currency Bias"
          data={briefing.currency_bias}
          options={CURRENCY_BIAS_OPTIONS}
          onChange={(cur, bias) => markUpdate(b => ({ ...b, currency_bias: { ...b.currency_bias, [cur]: setBiasEntry(b.currency_bias[cur], bias) } }))}
          onStrengthChange={(cur, strength) => markUpdate(b => ({ ...b, currency_bias: { ...b.currency_bias, [cur]: setStrengthEntry(b.currency_bias[cur], strength) } }))}
        />

        <BiasGrid
          title="Pair Bias"
          data={briefing.pair_bias}
          options={PAIR_BIAS_OPTIONS}
          onChange={(pair, bias) => markUpdate(b => ({ ...b, pair_bias: { ...b.pair_bias, [pair]: setBiasEntry(b.pair_bias[pair], bias) } }))}
          onStrengthChange={(pair, strength) => markUpdate(b => ({ ...b, pair_bias: { ...b.pair_bias, [pair]: setStrengthEntry(b.pair_bias[pair], strength) } }))}
        />

        <BiasGrid
          title="Asset Bias"
          data={briefing.asset_bias}
          options={PAIR_BIAS_OPTIONS.concat(CURRENCY_BIAS_OPTIONS).filter((v, i, a) => a.indexOf(v) === i)}
          onChange={(asset, bias) => markUpdate(b => ({ ...b, asset_bias: { ...b.asset_bias, [asset]: setBiasEntry(b.asset_bias[asset], bias) } }))}
          onStrengthChange={(asset, strength) => markUpdate(b => ({ ...b, asset_bias: { ...b.asset_bias, [asset]: setStrengthEntry(b.asset_bias[asset], strength) } }))}
        />

        <RuleEditor rules={briefing.rules} setRules={(rules) => markUpdate(b => ({ ...b, rules }))} />

        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground border-t border-border pt-3">
          <span>Válido até: <span className={expired ? 'text-red-400' : 'text-green-400'}>{briefing.valid_until ? new Date(briefing.valid_until).toLocaleString('pt-BR') : '-'}</span></span>
          <span>Arquivo: <span className="font-mono">market_briefing_today.json</span></span>
          <span>Rules: {briefing.rules.length}</span>
        </div>
      </div>

      <button onClick={save} disabled={saving || !briefing}
        className="flex items-center gap-1 text-xs px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-60">
        {saving ? 'Salvando...' : saved ? 'Salvo!' : 'Salvar Briefing'}
      </button>
    </div>
  );
}

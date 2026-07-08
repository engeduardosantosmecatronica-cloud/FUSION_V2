import { useEffect, useState } from 'react';
import { getMarketBriefing, updateMarketBriefing } from '@/services/api';
import { cn } from '@/lib/utils';
import { AlertTriangle, Save } from 'lucide-react';

const BIAS_OPTIONS = ['bullish', 'bearish', 'neutral'];
const BIAS_COLOR = { bullish: 'text-green-400', bearish: 'text-red-400', neutral: 'text-muted-foreground' };

export default function MarketBriefing() {
  const [briefing, setBriefing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => { getMarketBriefing().then(setBriefing); }, []);

  const save = async () => {
    setSaving(true);
    await updateMarketBriefing(briefing);
    setSaving(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!briefing) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  const expired = briefing.is_expired;

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Market Briefing</h1>
        {expired && (
          <span className="text-xs text-red-400 flex items-center gap-1 border border-red-700 rounded px-2 py-1">
            <AlertTriangle size={10} /> Briefing vencido — atualize
          </span>
        )}
      </div>

      <div className="bg-card border border-border rounded p-4 space-y-4">
        {/* Summary */}
        <div>
          <label className="text-xs text-muted-foreground uppercase">Resumo do Dia</label>
          <textarea value={briefing.summary} onChange={e => setBriefing(b => ({ ...b, summary: e.target.value }))}
            rows={3} className="mt-1 w-full bg-secondary border border-border rounded px-3 py-2 text-xs resize-none" />
        </div>

        {/* Risk Regime */}
        <div className="flex items-center gap-4">
          <label className="text-xs text-muted-foreground uppercase w-28">Risk Regime</label>
          <select value={briefing.risk_regime} onChange={e => setBriefing(b => ({ ...b, risk_regime: e.target.value }))}
            className="bg-secondary border border-border rounded px-2 py-1 text-xs">
            {['risk_on', 'risk_off', 'neutral'].map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>

        {/* Currency Bias */}
        <div>
          <div className="text-xs text-muted-foreground uppercase mb-2">Currency Bias</div>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(briefing.currency_bias).map(([cur, bias]) => (
              <div key={cur} className="flex items-center gap-2">
                <span className="text-xs font-bold w-8">{cur}</span>
                <select value={bias} onChange={e => setBriefing(b => ({ ...b, currency_bias: { ...b.currency_bias, [cur]: e.target.value } }))}
                  className={cn('bg-secondary border border-border rounded px-1 py-0.5 text-xs', BIAS_COLOR[bias])}>
                  {BIAS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            ))}
          </div>
        </div>

        {/* Pair Bias */}
        <div>
          <div className="text-xs text-muted-foreground uppercase mb-2">Pair Bias</div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(briefing.pair_bias).map(([pair, bias]) => (
              <div key={pair} className="flex items-center gap-2">
                <span className="text-xs font-bold w-16">{pair}</span>
                <select value={bias} onChange={e => setBriefing(b => ({ ...b, pair_bias: { ...b.pair_bias, [pair]: e.target.value } }))}
                  className={cn('bg-secondary border border-border rounded px-1 py-0.5 text-xs', BIAS_COLOR[bias])}>
                  {['buy', 'sell', 'neutral'].map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            ))}
          </div>
        </div>

        {/* Macro Rules */}
        <div>
          <div className="text-xs text-muted-foreground uppercase mb-2">Regras Macro</div>
          <div className="space-y-1">
            {briefing.macro_rules.map((rule, i) => (
              <div key={i} className="flex gap-2">
                <input value={rule} onChange={e => {
                  const rules = [...briefing.macro_rules];
                  rules[i] = e.target.value;
                  setBriefing(b => ({ ...b, macro_rules: rules }));
                }} className="flex-1 bg-secondary border border-border rounded px-2 py-1 text-xs" />
              </div>
            ))}
          </div>
        </div>

        {/* Validity */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>Válido até: <span className={expired ? 'text-red-400' : 'text-green-400'}>{new Date(briefing.valid_until).toLocaleString('pt-BR')}</span></span>
          <span>Atualizado: {new Date(briefing.last_updated).toLocaleTimeString('pt-BR')}</span>
        </div>
      </div>

      <button onClick={save} disabled={saving}
        className="flex items-center gap-1 text-xs px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90">
        <Save size={12} /> {saving ? 'Salvando...' : saved ? 'Salvo!' : 'Salvar Briefing'}
      </button>
    </div>
  );
}
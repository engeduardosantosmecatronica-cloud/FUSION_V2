import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Save, Shield } from 'lucide-react';

const DEFAULT_RISK = {
  lot_size: 0.01,
  stop_loss_pips: 20,
  take_profit_pips: 40,
  trailing_stop: false,
  trailing_pips: 10,
  max_daily_loss: 100,
  max_trades_day: 5,
  risk_per_trade: 1, // %
  auto_execute: false,
};

export default function RiskConfig({ config, onChange }) {
  const [local, setLocal] = useState(config || DEFAULT_RISK);
  const set = (k, v) => setLocal(prev => ({ ...prev, [k]: v }));

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-border flex items-center gap-2">
        <Shield className="w-3.5 h-3.5 text-blue-400" />
        <span className="text-xs font-semibold">Risco & Parâmetros</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">

        <Section title="Lote & Risco">
          <Row label="Volume (lotes)">
            <Input type="number" value={local.lot_size} step={0.01} min={0.01}
              onChange={e => set('lot_size', parseFloat(e.target.value))}
              className="h-7 w-24 text-xs font-mono bg-muted border-border text-right" />
          </Row>
          <Row label={`Risco por trade: ${local.risk_per_trade}%`}>
            <Slider value={[local.risk_per_trade]} min={0.1} max={5} step={0.1}
              onValueChange={([v]) => set('risk_per_trade', v)}
              className="w-28" />
          </Row>
        </Section>

        <Section title="Stop Loss & Take Profit">
          <Row label="Stop Loss (pips)">
            <Input type="number" value={local.stop_loss_pips} min={1}
              onChange={e => set('stop_loss_pips', parseInt(e.target.value))}
              className="h-7 w-24 text-xs font-mono bg-muted border-border text-right" />
          </Row>
          <Row label="Take Profit (pips)">
            <Input type="number" value={local.take_profit_pips} min={1}
              onChange={e => set('take_profit_pips', parseInt(e.target.value))}
              className="h-7 w-24 text-xs font-mono bg-muted border-border text-right" />
          </Row>
          <Row label="Trailing Stop">
            <Switch checked={local.trailing_stop} onCheckedChange={v => set('trailing_stop', v)} />
          </Row>
          {local.trailing_stop && (
            <Row label="Trailing (pips)">
              <Input type="number" value={local.trailing_pips} min={1}
                onChange={e => set('trailing_pips', parseInt(e.target.value))}
                className="h-7 w-24 text-xs font-mono bg-muted border-border text-right" />
            </Row>
          )}
        </Section>

        <Section title="Limites Operacionais">
          <Row label="Perda máx. diária ($)">
            <Input type="number" value={local.max_daily_loss} min={0}
              onChange={e => set('max_daily_loss', parseFloat(e.target.value))}
              className="h-7 w-24 text-xs font-mono bg-muted border-border text-right" />
          </Row>
          <Row label="Máx. trades/dia">
            <Input type="number" value={local.max_trades_day} min={1} max={100}
              onChange={e => set('max_trades_day', parseInt(e.target.value))}
              className="h-7 w-24 text-xs font-mono bg-muted border-border text-right" />
          </Row>
        </Section>

        <Section title="Execução">
          <Row label="Auto-executar sinais">
            <Switch checked={local.auto_execute} onCheckedChange={v => set('auto_execute', v)} />
          </Row>
          {local.auto_execute && (
            <p className="text-[10px] text-orange-400 bg-orange-400/10 rounded px-2 py-1.5">
              ⚠ Auto-execução requer bridge MT5 conectado
            </p>
          )}
        </Section>
      </div>

      <div className="p-3 border-t border-border">
        <Button onClick={() => onChange?.(local)} className="w-full h-8 text-xs gap-1.5">
          <Save className="w-3.5 h-3.5" />
          Salvar Configuração
        </Button>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="space-y-2">
      <p className="text-[9px] uppercase tracking-wider text-muted-foreground font-semibold">{title}</p>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div className="flex items-center justify-between">
      <Label className="text-[11px] text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
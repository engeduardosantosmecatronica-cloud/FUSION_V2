import React from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Settings2 } from 'lucide-react';

export default function IndicatorConfig({ config, onChange }) {
  const set = (key, value) => onChange({ ...config, [key]: value });

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-[11px] text-muted-foreground gap-1">
          <Settings2 className="w-3.5 h-3.5" />
          Indicadores
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 bg-card border-border p-4 space-y-3" align="end">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Indicadores</p>

        <Row label="EMA 1" period={config.ema1Period} color="#f59e0b"
          enabled={config.showEMA1}
          onToggle={v => set('showEMA1', v)}
          onPeriod={v => set('ema1Period', v)} />

        <Row label="EMA 2" period={config.ema2Period} color="#3b82f6"
          enabled={config.showEMA2}
          onToggle={v => set('showEMA2', v)}
          onPeriod={v => set('ema2Period', v)} />

        <Row label="EMA 3" period={config.ema3Period} color="#8b5cf6"
          enabled={config.showEMA3}
          onToggle={v => set('showEMA3', v)}
          onPeriod={v => set('ema3Period', v)} />

        <Row label="Bollinger" period={config.bollPeriod} color="#06b6d4"
          enabled={config.showBoll}
          onToggle={v => set('showBoll', v)}
          onPeriod={v => set('bollPeriod', v)} />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-[#a78bfa]" />
            <Label className="text-xs text-muted-foreground">RSI({config.rsiPeriod})</Label>
          </div>
          <div className="flex items-center gap-2">
            <Input type="number" value={config.rsiPeriod} min={2} max={50}
              onChange={e => set('rsiPeriod', parseInt(e.target.value))}
              className="h-6 w-14 text-xs font-mono bg-muted border-border text-center p-1" />
            <Switch checked={config.showRSI} onCheckedChange={v => set('showRSI', v)} />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-[#3b82f6]" />
            <Label className="text-xs text-muted-foreground">MACD</Label>
          </div>
          <Switch checked={config.showMACD} onCheckedChange={v => set('showMACD', v)} />
        </div>
      </PopoverContent>
    </Popover>
  );
}

function Row({ label, period, color, enabled, onToggle, onPeriod }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-3 h-0.5" style={{ background: color }} />
        <Label className="text-xs text-muted-foreground">{label}({period})</Label>
      </div>
      <div className="flex items-center gap-2">
        <Input type="number" value={period} min={2} max={200}
          onChange={e => onPeriod(parseInt(e.target.value))}
          className="h-6 w-14 text-xs font-mono bg-muted border-border text-center p-1" />
        <Switch checked={enabled} onCheckedChange={onToggle} />
      </div>
    </div>
  );
}
import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { Save } from "lucide-react";

const defaultConfig = {
  symbol: "AUDUSD",
  timeframe: "M15",
  volume: 0.01,
  mode: "automatic",
  stop_loss: 0,
  take_profit: 0,
  risk_per_trade_pct: 0.25,
  max_daily_loss: 1000,
  max_drawdown_pct: 5,
  daily_target: 200,
  min_rr_ratio: 1.5,
  max_spread: 8,
  trading_start_hour: 8,
  trading_end_hour: 20,
  max_daily_trades: 3,
  block_consecutive_losses: 3,
  auto_reconnect: true,
  block_on_news: true,
  trailing_stop_enabled: true,
  breakeven_enabled: false,
  trailing_stop_distance: 20,
  trailing_activation: 10,
};

export default function Settings() {
  const [config, setConfig] = useState(defaultConfig);
  const [runtime, setRuntime] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fusionApi.runtime();
        setRuntime(data);
        const trading = data?.trading || {};
        const risk = data?.risk || {};
        setConfig({
          ...defaultConfig,
          symbol: data?.symbol || data?.symbols?.[0] || defaultConfig.symbol,
          timeframe: data?.timeframe || data?.timeframes?.[0] || defaultConfig.timeframe,
          volume: Number(trading.volume || risk.min_lot || defaultConfig.volume),
          mode: trading.execution_mode || defaultConfig.mode,
          stop_loss: Number(trading.stop_loss || defaultConfig.stop_loss),
          take_profit: Number(trading.take_profit || defaultConfig.take_profit),
          risk_per_trade_pct: Number(risk.max_risk_per_trade || defaultConfig.risk_per_trade_pct),
          max_daily_loss: Number(risk.max_daily_loss || defaultConfig.max_daily_loss),
          max_drawdown_pct: Number(risk.max_drawdown_pct || defaultConfig.max_drawdown_pct),
          daily_target: Number(risk.daily_target || defaultConfig.daily_target),
          min_rr_ratio: Number(risk.min_rr_ratio || defaultConfig.min_rr_ratio),
          max_spread: Number(risk.max_spread || defaultConfig.max_spread),
          auto_reconnect: Boolean(trading.auto_reconnect ?? defaultConfig.auto_reconnect),
          block_on_news: Boolean(trading.block_on_news ?? defaultConfig.block_on_news),
          trailing_stop_enabled: Boolean(trading.trailing_stop_enabled ?? defaultConfig.trailing_stop_enabled),
          breakeven_enabled: Boolean(trading.breakeven_enabled ?? defaultConfig.breakeven_enabled),
          trailing_stop_distance: Number(trading.trailing_stop_distance || defaultConfig.trailing_stop_distance),
          trailing_activation: Number(trading.trailing_activation || defaultConfig.trailing_activation),
        });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  async function save() {
    setSaving(true);
    try {
      const payload = {
        ...(runtime || {}),
        symbol: config.symbol,
        timeframe: config.timeframe,
        trading: {
          ...((runtime && runtime.trading) || {}),
          execution_mode: config.mode,
          allow_new_orders: true,
          volume: config.volume,
          stop_loss: config.stop_loss,
          take_profit: config.take_profit,
          auto_reconnect: config.auto_reconnect,
          block_on_news: config.block_on_news,
          trailing_stop_enabled: config.trailing_stop_enabled,
          breakeven_enabled: config.breakeven_enabled,
          trailing_stop_distance: config.trailing_stop_distance,
          trailing_activation: config.trailing_activation,
        },
        risk: {
          ...((runtime && runtime.risk) || {}),
          max_risk_per_trade: config.risk_per_trade_pct,
          max_daily_loss: config.max_daily_loss,
          max_drawdown_pct: config.max_drawdown_pct,
          daily_target: config.daily_target,
          min_rr_ratio: config.min_rr_ratio,
          max_spread: config.max_spread,
        },
      };
      const updated = await fusionApi.updateRuntime(payload);
      setRuntime(updated);
      toast({ title: "Configurações salvas" });
    } catch (error) {
      toast({ title: "Falha ao salvar", description: error.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  }

  function upd(field, value) {
    setConfig((current) => ({ ...current, [field]: value }));
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-bold tracking-tight">Configurações</h1><Button className="bg-emerald-500 hover:bg-emerald-600 text-white" onClick={save} disabled={saving}><Save className="w-4 h-4 mr-1" /> {saving ? "Salvando..." : "Salvar"}</Button></div>
      <section className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Parâmetros de Trading</h2><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><Label className="text-xs text-gray-400">Ativo</Label><Input className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.symbol} onChange={(e) => upd("symbol", e.target.value)} /></div><div><Label className="text-xs text-gray-400">Timeframe</Label><Select value={config.timeframe} onValueChange={(value) => upd("timeframe", value)}><SelectTrigger className="bg-[#1a2035] border-[#2a3555] text-white mt-1"><SelectValue /></SelectTrigger><SelectContent className="bg-[#1a2035] border-[#2a3555] text-white">{["M1", "M5", "M15", "M30", "H1", "H4", "D1"].map((tf) => <SelectItem key={tf} value={tf}>{tf}</SelectItem>)}</SelectContent></Select></div><div><Label className="text-xs text-gray-400">Volume (lotes)</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.volume} onChange={(e) => upd("volume", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Modo</Label><Select value={config.mode} onValueChange={(value) => upd("mode", value)}><SelectTrigger className="bg-[#1a2035] border-[#2a3555] text-white mt-1"><SelectValue /></SelectTrigger><SelectContent className="bg-[#1a2035] border-[#2a3555] text-white"><SelectItem value="automatic">Automático</SelectItem><SelectItem value="semi_automatic">Semi-automático</SelectItem><SelectItem value="read_only">Somente leitura</SelectItem></SelectContent></Select></div><div><Label className="text-xs text-gray-400">Stop Loss</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.stop_loss} onChange={(e) => upd("stop_loss", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Take Profit</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.take_profit} onChange={(e) => upd("take_profit", Number(e.target.value))} /></div></div></section>
      <section className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Gestão de Risco</h2><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><Label className="text-xs text-gray-400">Risco por operação (%)</Label><Input type="number" step="0.1" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.risk_per_trade_pct} onChange={(e) => upd("risk_per_trade_pct", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Perda diária máx.</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.max_daily_loss} onChange={(e) => upd("max_daily_loss", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Drawdown máx. (%)</Label><Input type="number" step="0.1" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.max_drawdown_pct} onChange={(e) => upd("max_drawdown_pct", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Meta diária</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.daily_target} onChange={(e) => upd("daily_target", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">R:R mínimo</Label><Input type="number" step="0.1" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.min_rr_ratio} onChange={(e) => upd("min_rr_ratio", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Spread máximo</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.max_spread} onChange={(e) => upd("max_spread", Number(e.target.value))} /></div></div></section>
      <section className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Controle Operacional</h2><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><Label className="text-xs text-gray-400">Horário início</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.trading_start_hour} onChange={(e) => upd("trading_start_hour", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Horário fim</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.trading_end_hour} onChange={(e) => upd("trading_end_hour", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Máx. trades/dia</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.max_daily_trades} onChange={(e) => upd("max_daily_trades", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Bloqueio perdas consec.</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.block_consecutive_losses} onChange={(e) => upd("block_consecutive_losses", Number(e.target.value))} /></div></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2"><div className="flex items-center justify-between"><Label className="text-xs text-gray-400">Reconexão automática</Label><Switch checked={config.auto_reconnect} onCheckedChange={(value) => upd("auto_reconnect", value)} /></div><div className="flex items-center justify-between"><Label className="text-xs text-gray-400">Bloquear em notícias</Label><Switch checked={config.block_on_news} onCheckedChange={(value) => upd("block_on_news", value)} /></div><div className="flex items-center justify-between"><Label className="text-xs text-gray-400">Trailing Stop</Label><Switch checked={config.trailing_stop_enabled} onCheckedChange={(value) => upd("trailing_stop_enabled", value)} /></div><div className="flex items-center justify-between"><Label className="text-xs text-gray-400">Break-even</Label><Switch checked={config.breakeven_enabled} onCheckedChange={(value) => upd("breakeven_enabled", value)} /></div></div>{config.trailing_stop_enabled && <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2"><div><Label className="text-xs text-gray-400">Trailing distância</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.trailing_stop_distance} onChange={(e) => upd("trailing_stop_distance", Number(e.target.value))} /></div><div><Label className="text-xs text-gray-400">Ativação trailing</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" value={config.trailing_activation} onChange={(e) => upd("trailing_activation", Number(e.target.value))} /></div></div>}</section>
    </div>
  );
}

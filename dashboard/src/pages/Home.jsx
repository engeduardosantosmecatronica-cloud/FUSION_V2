import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import StatusCard from "@/components/dashboard/StatusCard";
import RobotStatusBadge from "@/components/dashboard/RobotStatusBadge";
import { Wallet, TrendingUp, TrendingDown, ShieldAlert, BarChart3, Activity, Cpu, Zap, Play, Pause, Square, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";

export default function Home() {
  const [runtime, setRuntime] = useState(null);
  const [health, setHealth] = useState(null);
  const [status, setStatus] = useState(null);
  const [orders, setOrders] = useState([]);
  const [signals, setSignals] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [models, setModels] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    let cancelled = false;
    const loadData = async () => {
      try {
        const [api, system, rt, ord, sig, evt, mdl, perf] = await Promise.all([
          fusionApi.health(),
          fusionApi.status(),
          fusionApi.runtime(),
          fusionApi.orders(),
          fusionApi.signals(),
          fusionApi.alerts(),
          fusionApi.models(),
          fusionApi.performance(),
        ]);
        if (cancelled) return;
        setHealth(api);
        setStatus(system);
        setRuntime(rt);
        setOrders(Array.isArray(ord) ? ord : []);
        setSignals(Array.isArray(sig) ? sig : []);
        setAlerts(Array.isArray(evt) ? evt : []);
        setModels(Array.isArray(mdl) ? mdl : []);
        setPerformance(perf || null);
      } catch (error) {
        if (!cancelled) {
          setAlerts([]);
          setSignals([]);
          setOrders([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadData();
    const timer = setInterval(loadData, 5000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  async function setRobotStatus(nextStatus) {
    const enabled = nextStatus === "running";
    const updated = {
      ...(runtime || {}),
      trading: {
        ...((runtime && runtime.trading) || {}),
        allow_new_orders: enabled,
        execution_mode: enabled ? "automatic" : "read_only",
      },
    };
    try {
      const payload = await fusionApi.updateRuntime(updated);
      setRuntime(payload);
      toast({ title: enabled ? "Robô liberado" : "Robô pausado" });
    } catch (error) {
      toast({ title: "Falha ao atualizar runtime", description: error.message, variant: "destructive" });
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  const operational = Boolean(health?.status === "ok" && status?.fusion?.status === "online");
  const robotStatus = operational ? (runtime?.trading?.allow_new_orders === false ? "paused" : "running") : "stopped";
  const mt5Connected = Boolean(health?.mt5_ready || status?.mt5?.status === "online");
  const latestSignal = signals[0];
  const consensus = latestSignal?.decision || "WAIT";
  const consensusConfidence = Number(latestSignal?.confidence || 0) * 100;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Painel de Controle</h1>
          <p className="text-sm text-gray-500 mt-1">Visão do sistema Fusion com dados do backend</p>
        </div>
        <div className="flex items-center gap-2">
          <RobotStatusBadge status={robotStatus} />
          <div className="flex gap-1 ml-2">
            <Button size="sm" variant="ghost" className="text-emerald-400 hover:bg-emerald-400/10" onClick={() => setRobotStatus("running")} disabled={robotStatus === "running"}><Play className="w-4 h-4" /></Button>
            <Button size="sm" variant="ghost" className="text-amber-400 hover:bg-amber-400/10" onClick={() => setRobotStatus("paused")} disabled={robotStatus === "paused"}><Pause className="w-4 h-4" /></Button>
            <Button size="sm" variant="ghost" className="text-red-400 hover:bg-red-400/10" onClick={() => setRobotStatus("stopped")} disabled={robotStatus === "stopped"}><Square className="w-4 h-4" /></Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard icon={Wallet} label="Sinais" value={signals.length} sub={latestSignal ? `${latestSignal.symbol} • ${latestSignal.timeframe}` : "Sem sinal recente"} color="text-white" />
        <StatusCard icon={orders.length ? TrendingUp : TrendingDown} label="Ordens Abertas" value={orders.length} color={orders.length ? "text-emerald-400" : "text-amber-400"} sub={`${performance?.totals?.signals_executed || 0} execuções`} />
        <StatusCard icon={ShieldAlert} label="Alertas" value={alerts.length} color="text-red-400" sub={alerts[0]?.message || "Nenhum alerta ativo"} />
        <StatusCard icon={BarChart3} label="Modelos" value={models.length} color="text-blue-400" sub={`${performance?.totals?.total_signals || 0} sinais totais`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2"><Activity className="w-4 h-4 text-emerald-400" />Saúde do Sistema</h2>
          <div className="space-y-3">
            {[{ label: "MT5", value: mt5Connected ? "Conectado" : "Desconectado", ok: mt5Connected }, { label: "API Fusion", value: health?.status === "ok" ? "Ativa" : "Inativa", ok: health?.status === "ok" }, { label: "Backend", value: status?.backend?.status || "indisponível", ok: status?.backend?.status === "online" }, { label: "Feed", value: status?.feed?.status || "indisponível", ok: status?.feed?.status === "online" }, { label: "Loja de Modelos", value: `${models.length} carregados`, ok: models.length > 0 }, { label: "Uptime", value: status?.fusion?.last_cycle ? new Date(status.fusion.last_cycle).toLocaleTimeString("pt-BR") : "sem ciclo", ok: true }].map((item) => (
              <div key={item.label} className="flex items-center justify-between"><span className="text-sm text-gray-400">{item.label}</span><span className={`text-sm font-medium ${item.ok ? "text-emerald-400" : "text-red-400"}`}>{item.value}</span></div>
            ))}
          </div>
        </div>

        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2"><Cpu className="w-4 h-4 text-blue-400" />Consenso IA</h2>
          <div className="flex items-center gap-4 mb-4">
            <span className={`text-3xl font-black ${consensus === "BUY" ? "text-emerald-400" : consensus === "SELL" ? "text-red-400" : "text-gray-400"}`}>{consensus}</span>
            <div>
              <p className="text-sm text-gray-400">Confiança: <span className="text-white font-semibold">{consensusConfidence.toFixed(0)}%</span></p>
              <p className="text-sm text-gray-400">Status: <span className="text-emerald-400 font-semibold">{latestSignal?.status || "sem sinal"}</span></p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {signals.slice(0, 2).map((signal) => (
              <div key={`${signal.symbol}-${signal.timeframe}-${signal.id}`} className="bg-[#1a2035] rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">{signal.symbol} • {signal.timeframe}</p>
                <p className="text-sm font-semibold text-white">{signal.decision}</p>
                <p className="text-xs text-gray-500 mt-1">Confiança: {(Number(signal.confidence || 0) * 100).toFixed(0)}%</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Zap className="w-4 h-4 text-amber-400" />Operações Ativas</h2>
          {orders.length === 0 ? <p className="text-sm text-gray-600">Nenhuma posição aberta.</p> : <div className="space-y-2">{orders.slice(0, 5).map((order) => <div key={order.ticket || order.id} className="flex items-center justify-between py-2 border-b border-[#1e2740] last:border-0"><div><span className={`text-xs font-bold px-1.5 py-0.5 rounded ${order.direction === "BUY" ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"}`}>{order.direction || "—"}</span><span className="text-sm text-gray-300 ml-2">{order.symbol || "—"}</span></div><span className="text-sm text-gray-400">{order.lots || order.volume || "—"}</span></div>)}</div>}
        </div>

        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-red-400" />Eventos Recentes</h2>
          {alerts.length === 0 ? <p className="text-sm text-gray-600">Nenhum evento registrado.</p> : <div className="space-y-2">{alerts.slice(0, 5).map((event) => <div key={event.id} className="flex items-start gap-2 py-2 border-b border-[#1e2740] last:border-0"><span className={`text-xs font-bold uppercase mt-0.5 ${event.severity === "error" ? "text-red-400" : event.severity === "warning" ? "text-amber-400" : "text-blue-400"}`}>{event.severity || "info"}</span><p className="text-sm text-gray-300">{event.message}</p></div>)}</div>}
        </div>
      </div>

      <p className="text-xs text-gray-600 text-center">Atualizado: {new Date().toLocaleTimeString("pt-BR")}</p>
    </div>
  );
}

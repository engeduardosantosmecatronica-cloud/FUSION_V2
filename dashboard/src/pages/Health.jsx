import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { Activity, Wifi, WifiOff, Cpu, HardDrive, Clock, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

function HealthItem({ label, value, ok, icon: Icon }) {
  return <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 flex items-center gap-3">
    <div className={ok ? "p-2 rounded-lg bg-emerald-400/10" : "p-2 rounded-lg bg-red-400/10"}><Icon className={ok ? "w-4 h-4 text-emerald-400" : "w-4 h-4 text-red-400"} /></div>
    <div className="flex-1"><p className="text-xs text-gray-500">{label}</p><p className={ok ? "text-sm font-semibold text-emerald-400" : "text-sm font-semibold text-red-400"}>{value}</p></div>
    {ok ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
  </div>;
}

export default function Health() {
  const [health, setHealth] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [api, system] = await Promise.all([fusionApi.health(), fusionApi.status()]);
        setHealth(api); setStatus(system); setError("");
      } catch (err) { setError(err.message); }
    };
    load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, []);

  const mt5Ready = Boolean(health?.mt5_ready && status?.mt5?.status === "online");
  const feedReady = status?.feed?.status === "online";
  const backendReady = status?.backend?.status === "online";
  const operational = mt5Ready && feedReady && backendReady;

  return <div className="space-y-6">
    <div className="flex items-center justify-between"><h1 className="text-2xl font-bold tracking-tight">Saúde do Sistema</h1>
      <span className={operational ? "px-3 py-1.5 rounded-full text-sm font-semibold text-emerald-400 bg-emerald-400/10" : "px-3 py-1.5 rounded-full text-sm font-semibold text-red-400 bg-red-400/10"}>{operational ? "Operacional" : "Degradado"}</span>
    </div>
    {error && <div className="text-red-400 bg-red-500/10 border border-red-500/30 rounded p-3">{error}</div>}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      <HealthItem label="MetaTrader 5" value={mt5Ready ? "Conectado" : "Desconectado"} ok={mt5Ready} icon={mt5Ready ? Wifi : WifiOff} />
      <HealthItem label="API Fusion" value={health?.status === "ok" ? "Ativa" : "Inativa"} ok={health?.status === "ok"} icon={Activity} />
      <HealthItem label="Backend" value={status?.backend?.status || "indisponível"} ok={backendReady} icon={Cpu} />
      <HealthItem label="Feed de Mercado" value={status?.feed?.status || "indisponível"} ok={feedReady} icon={Clock} />
      <HealthItem label="Último Candle" value={status?.feed?.last_candle || "sem dados"} ok={feedReady} icon={Clock} />
      <HealthItem label="Posições Abertas" value={String(status?.open_orders ?? 0)} ok={true} icon={Activity} />
      <HealthItem label="Erro Crítico" value={status?.last_critical_error || "Nenhum"} ok={!status?.last_critical_error} icon={status?.last_critical_error ? AlertTriangle : CheckCircle} />
      <HealthItem label="Serviço" value={health?.service || "Fusion API"} ok={health?.status === "ok"} icon={HardDrive} />
    </div>
    <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Diagnóstico em tempo real</h2>
      <div className="space-y-2 text-sm text-gray-300"><p>Fusion: {status?.fusion?.status || "sem resposta"}</p><p>MT5: {status?.mt5?.status || "sem resposta"}</p><p>Feed: {status?.feed?.status || "sem resposta"}</p><p>Última verificação: {new Date().toLocaleString("pt-BR")}</p></div>
    </div>
  </div>;
}
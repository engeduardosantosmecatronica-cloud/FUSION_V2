import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { Cpu, CheckCircle, XCircle } from "lucide-react";

export default function Signals() {
  const [signals, setSignals] = useState([]);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [sig, mdl] = await Promise.all([fusionApi.signals(), fusionApi.models()]);
        if (!cancelled) {
          setSignals(Array.isArray(sig) ? sig : []);
          setModels(Array.isArray(mdl) ? mdl : []);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, 5000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  const latest = signals[0];
  const consensus = latest?.decision || "WAIT";
  const confidence = Number(latest?.confidence || 0) * 100;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Sinais e Decisões</h1>
        <p className="text-sm text-gray-500 mt-1">Consenso e modelos ativos do Fusion</p>
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-6 flex flex-col sm:flex-row items-center gap-6">
        <div className="text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Consenso</p>
          <span className={`text-5xl font-black ${consensus === "BUY" ? "text-emerald-400" : consensus === "SELL" ? "text-red-400" : "text-gray-400"}`}>{consensus}</span>
        </div>
        <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center"><p className="text-xs text-gray-500">Confiança</p><p className="text-xl font-bold text-white">{confidence.toFixed(0)}%</p></div>
          <div className="text-center"><p className="text-xs text-gray-500">Status</p><p className="text-xl font-bold text-emerald-400">{latest?.status || "—"}</p></div>
          <div className="text-center"><p className="text-xs text-gray-500">Símbolo</p><p className="text-xl font-bold text-blue-400">{latest?.symbol || "—"}</p></div>
          <div className="text-center"><p className="text-xs text-gray-500">TF</p><p className="text-xl font-bold text-gray-300">{latest?.timeframe || "—"}</p></div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {models.length === 0 ? <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 text-gray-500">Nenhum modelo disponível no backend.</div> : models.slice(0, 2).map((model) => (
          <div key={model.id || model.name} className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between"><div className="flex items-center gap-2"><Cpu className="w-4 h-4 text-blue-400" /><h3 className="text-sm font-semibold text-white">{model.name}</h3></div><span className="text-xs text-gray-500">{model.version || "—"}</span></div>
            <div className="flex items-center gap-3"><span className={`text-2xl font-black ${model.status === "disponivel" ? "text-emerald-400" : "text-amber-400"}`}>{model.status || "—"}</span><span className="text-sm text-gray-500">Confiança: {model.avg_confidence ? `${(model.avg_confidence * 100).toFixed(0)}%` : "—"}</span></div>
            <div className="text-xs text-gray-500">Caminho: {model.path || "—"}</div>
          </div>
        ))}
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Razões da Decisão</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div><p className="text-xs text-emerald-400 font-semibold mb-2 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Fatores Favoráveis</p><ul className="space-y-1 text-sm text-gray-300"><li>• {latest?.reason || "Sinal recente do Fusion"}</li><li>• Confiança atual: {(confidence).toFixed(0)}%</li></ul></div>
          <div><p className="text-xs text-red-400 font-semibold mb-2 flex items-center gap-1"><XCircle className="w-3 h-3" /> Fatores Contrários</p><ul className="space-y-1 text-sm text-gray-300"><li>• Status: {latest?.status || "sem bloqueio"}</li><li>• Estratégia: {latest?.strategy || "—"}</li></ul></div>
        </div>
      </div>
    </div>
  );
}
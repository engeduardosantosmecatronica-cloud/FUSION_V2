import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { Layers, Trophy } from "lucide-react";

export default function Strategies() {
  const [filters, setFilters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fusionApi.filters();
        if (!cancelled) setFilters(Array.isArray(data) ? data : []);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Estratégias</h1>
        <p className="text-sm text-gray-500 mt-1">Filtros e bloqueios do motor Fusion</p>
      </div>

      {filters.length === 0 ? <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-12 text-center"><Layers className="w-10 h-10 text-gray-600 mx-auto mb-3" /><p className="text-gray-500">Nenhuma estratégia retornada pelo backend</p></div> : <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{filters.map((filter) => <div key={filter.name} className={`bg-[#0f1423] border rounded-xl p-5 ${filter.mode === "block" ? "border-red-500/30" : "border-[#1e2740]"}`}><div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2"><Trophy className={`w-4 h-4 ${filter.mode === "block" ? "text-red-400" : "text-emerald-400"}`} /><h3 className="text-sm font-semibold text-white">{filter.name}</h3></div><span className="text-xs text-gray-500">{filter.mode}</span></div><p className="text-xs text-gray-500 mb-3">{filter.last_reason || "Sem razão recente"}</p><div className="grid grid-cols-3 gap-2 text-center"><div className="bg-[#1a2035] rounded-lg p-2"><p className="text-xs text-gray-500">Bloqueios</p><p className="text-sm font-bold text-white">{filter.total_blocks}</p></div><div className="bg-[#1a2035] rounded-lg p-2"><p className="text-xs text-gray-500">Shadow</p><p className="text-sm font-bold text-emerald-400">{filter.shadow_events || 0}</p></div><div className="bg-[#1a2035] rounded-lg p-2"><p className="text-xs text-gray-500">Recomendação</p><p className="text-sm font-bold text-amber-400">{filter.recommendation || "monitorar"}</p></div></div></div>)}</div>}
    </div>
  );
}

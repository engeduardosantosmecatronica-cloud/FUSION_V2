import React, { useState, useEffect } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { ScrollText } from "lucide-react";

export default function Logs() {
  const [events, setEvents] = useState(/** @type {Array<any>} */ ([]));
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fusionApi.logs();
        if (!cancelled) setEvents(Array.isArray(data) ? data : []);
      } catch (error) {
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    const timer = setInterval(load, 3000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  const types = ["all", "signal", "order", "risk", "system", "model", "market", "error"];
  const filtered = typeFilter === "all" ? events : events.filter((e) => String(e.type || "").toLowerCase() === typeFilter);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Logs do Sistema</h1>
        <div className="flex gap-1 flex-wrap">
          {types.map(t => (
            <button key={t} onClick={() => setTypeFilter(t)} className={`px-2.5 py-1 rounded text-xs font-medium ${typeFilter === t ? "bg-[#1a2035] text-white" : "text-gray-500 hover:text-gray-300"}`}>
              {t === "all" ? "Todos" : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <ScrollText className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">Nenhum log encontrado</p>
          </div>
        ) : (
          <div className="font-mono text-xs max-h-[600px] overflow-y-auto">
            {filtered.map((e) => {
              const severity = String(e.severity || "info").toLowerCase();
              const sevColor = { info: "text-blue-400", warning: "text-amber-400", error: "text-red-400", critical: "text-red-500" };
              const timestamp = e.timestamp || e.created_date || e.createdAt || "";
              return (
                <div key={e.id || `${e.type}-${timestamp}`} className="flex gap-3 px-4 py-2 border-b border-[#1e2740]/30 hover:bg-white/[0.02]">
                  <span className="text-gray-600 flex-shrink-0">{timestamp ? new Date(timestamp).toLocaleString("pt-BR") : "—"}</span>
                  <span className={`font-semibold flex-shrink-0 uppercase w-16 ${sevColor[severity] || "text-gray-400"}`}>{severity}</span>
                  <span className="text-gray-500 flex-shrink-0 w-16">[{String(e.type || "info")}]</span>
                  <span className="text-gray-300">{e.message}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
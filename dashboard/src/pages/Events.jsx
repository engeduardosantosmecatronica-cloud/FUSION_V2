import React, { useState, useEffect } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { Bell } from "lucide-react";

const sevColors = {
  info: "bg-blue-400/10 text-blue-400 border-blue-400/20",
  warning: "bg-amber-400/10 text-amber-400 border-amber-400/20",
  error: "bg-red-400/10 text-red-400 border-red-400/20",
  critical: "bg-red-500/10 text-red-500 border-red-500/20",
};
const typeLabels = { signal: "Sinal", order: "Ordem", risk: "Risco", system: "Sistema", model: "Modelo", market: "Mercado", error: "Erro" };

export default function Events() {
  const [events, setEvents] = useState(/** @type {Array<any>} */ ([]));
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fusionApi.alerts();
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

  const filtered = filter === "all" ? events : events.filter((e) => String(e.severity || "info").toLowerCase() === filter);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Eventos e Alertas</h1>
          <p className="text-sm text-gray-500 mt-1">{events.length} eventos registrados</p>
        </div>
        <div className="flex gap-1">
          {["all", "info", "warning", "error", "critical"].map(s => (
            <button key={s} onClick={() => setFilter(s)} className={`px-2.5 py-1 rounded text-xs font-medium transition ${filter === s ? "bg-[#1a2035] text-white" : "text-gray-500 hover:text-gray-300"}`}>
              {s === "all" ? "Todos" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-12 text-center">
          <Bell className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">Nenhum evento encontrado</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((e) => {
            const severity = String(e.severity || "info").toLowerCase();
            const eventType = String(e.type || "system").toLowerCase();
            const createdAt = e.timestamp || e.created_date || e.createdAt || "";
            return (
              <div key={e.id || `${eventType}-${createdAt}`} className={`bg-[#0f1423] border rounded-xl p-4 flex items-start gap-3 ${sevColors[severity]?.split(" ")[2] || "border-[#1e2740]"}`}>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${sevColors[severity] || ""}`}>{severity}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs text-gray-500">{typeLabels[eventType] || e.type}</span>
                    {e.symbol && <span className="text-xs text-gray-600">• {e.symbol}</span>}
                    <span className="text-xs text-gray-600 ml-auto">{createdAt ? new Date(createdAt).toLocaleString("pt-BR") : "—"}</span>
                  </div>
                  <p className="text-sm text-gray-200">{e.message}</p>
                  {e.details && <p className="text-xs text-gray-500 mt-1">{e.details}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
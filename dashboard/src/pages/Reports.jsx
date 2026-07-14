import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";

export default function Reports() {
  const [performance, setPerformance] = useState(null);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [perf, sig] = await Promise.all([fusionApi.performance(), fusionApi.signals()]);
        if (!cancelled) {
          setPerformance(perf || null);
          setSignals(Array.isArray(sig) ? sig : []);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, 5000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  const totals = performance?.totals || {};
  const totalPnl = Number(totals.total_profit || 0);
  const totalSignals = Number(totals.total_signals || 0);
  const blockedSignals = Number(totals.signals_blocked || 0);
  const executedSignals = Number(totals.signals_executed || 0);
  const pnlData = (performance?.by_symbol || []).slice(0, 8).map((item) => ({ label: item.symbol || "—", pnl: Number(item.total_profit || 0) }));
  const equityData = pnlData.map((item, index) => ({ label: item.label, equity: totalPnl + index * 100 }));

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Relatórios</h1>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { l: "P&L Total", v: `R$ ${totalPnl.toFixed(2)}`, c: totalPnl >= 0 ? "text-emerald-400" : "text-red-400" },
          { l: "Sinais", v: totalSignals, c: "text-blue-400" },
          { l: "Bloqueados", v: blockedSignals, c: "text-amber-400" },
          { l: "Executados", v: executedSignals, c: "text-emerald-400" },
          { l: "Último", v: signals[0]?.decision || "—", c: "text-white" },
        ].map((s) => (
          <div key={s.l} className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500">{s.l}</p>
            <p className={`text-lg font-bold ${s.c}`}>{s.v}</p>
          </div>
        ))}
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Curva de Patrimônio</h2>{equityData.length === 0 ? <p className="text-gray-600 text-center py-8 text-sm">Nenhum dado</p> : <ResponsiveContainer width="100%" height={250}><LineChart data={equityData}><XAxis dataKey="label" tick={{ fill: "#6b7280", fontSize: 10 }} /><YAxis tick={{ fill: "#6b7280", fontSize: 10 }} /><Tooltip contentStyle={{ background: "#1a2035", border: "1px solid #2a3555", borderRadius: 8, color: "#fff", fontSize: 12 }} /><Line type="monotone" dataKey="equity" stroke="#10b981" dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer>}</div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">P&L por Símbolo</h2>{pnlData.length === 0 ? <p className="text-gray-600 text-center py-8 text-sm">Nenhum dado</p> : <ResponsiveContainer width="100%" height={200}><BarChart data={pnlData}><XAxis dataKey="label" tick={{ fill: "#6b7280", fontSize: 10 }} /><YAxis tick={{ fill: "#6b7280", fontSize: 10 }} /><Tooltip contentStyle={{ background: "#1a2035", border: "1px solid #2a3555", borderRadius: 8, color: "#fff", fontSize: 12 }} /><Bar dataKey="pnl" radius={[4, 4, 0, 0]}>{pnlData.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? "#10b981" : "#ef4444"} />)}</Bar></BarChart></ResponsiveContainer>}</div>
    </div>
  );
}

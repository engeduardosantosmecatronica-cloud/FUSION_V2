import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Briefcase, TrendingUp, TrendingDown, Shield } from "lucide-react";
import StatusCard from "@/components/dashboard/StatusCard";

export default function Portfolio() {
  const [orders, setOrders] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [ord, perf] = await Promise.all([fusionApi.orders(), fusionApi.performance()]);
        if (!cancelled) {
          setOrders(Array.isArray(ord) ? ord : []);
          setPerformance(perf || null);
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
  const winRate = Number(totals.win_rate || 0);
  const totalSignals = Number(totals.total_signals || 0);
  const blockedSignals = Number(totals.signals_blocked || 0);
  const executedSignals = Number(totals.signals_executed || 0);
  const chartData = (performance?.by_symbol || []).slice(0, 8).map((item) => ({ name: item.symbol || "—", pnl: Number(item.total_profit || 0) }));

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Portfólio</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard icon={Briefcase} label="Posições Abertas" value={orders.length} sub={`${executedSignals} execuções`} color="text-blue-400" />
        <StatusCard icon={totalPnl >= 0 ? TrendingUp : TrendingDown} label="P&L Total" value={`R$ ${totalPnl.toFixed(2)}`} color={totalPnl >= 0 ? "text-emerald-400" : "text-red-400"} />
        <StatusCard icon={Shield} label="Taxa Acerto" value={`${winRate.toFixed(1)}%`} color="text-purple-400" sub={`${totalSignals} sinais`} />
        <StatusCard icon={TrendingUp} label="Bloqueios" value={blockedSignals} color="text-amber-400" sub={`Ativas: ${orders.length}`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">P&L por Símbolo</h2>
          {chartData.length === 0 ? <p className="text-gray-600 text-sm text-center py-8">Nenhum dado disponível</p> : <ResponsiveContainer width="100%" height={250}><BarChart data={chartData}><XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 10 }} /><YAxis tick={{ fill: "#6b7280", fontSize: 10 }} /><Tooltip contentStyle={{ background: "#1a2035", border: "1px solid #2a3555", borderRadius: 8, color: "#fff", fontSize: 12 }} /><Bar dataKey="pnl" radius={[4, 4, 0, 0]}>{chartData.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? "#10b981" : "#ef4444"} />)}</Bar></BarChart></ResponsiveContainer>}
        </div>
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Posições Ativas</h2>
          {orders.length === 0 ? <p className="text-gray-600 text-sm text-center py-8">Nenhuma posição</p> : <div className="space-y-2">{orders.map((order) => <div key={order.ticket || order.id} className="flex items-center justify-between rounded-lg bg-[#1a2035] px-3 py-2"><div><p className="text-sm font-semibold text-white">{order.symbol || "—"}</p><p className="text-xs text-gray-500">{order.direction || "—"}</p></div><span className="text-sm text-emerald-400">{order.lots || order.volume || "—"}</span></div>)}</div>}
        </div>
      </div>
    </div>
  );
}

import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { FlaskConical, Play } from "lucide-react";

export default function Backtest() {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);

  function runBacktest() {
    setRunning(true);
    setTimeout(() => {
      const trades = [];
      let equity = 100000;
      const equityCurve = [{ trade: 0, equity }];
      for (let i = 1; i <= 120; i++) {
        const pnl = (Math.random() - 0.45) * 600;
        equity += pnl;
        equityCurve.push({ trade: i, equity: Math.round(equity) });
        trades.push({ id: i, pnl: Math.round(pnl) });
      }
      const wins = trades.filter(t => t.pnl > 0);
      const losses = trades.filter(t => t.pnl < 0);
      const grossProfit = wins.reduce((s, t) => s + t.pnl, 0);
      const grossLoss = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
      setResults({
        equityCurve,
        totalTrades: trades.length,
        wins: wins.length,
        losses: losses.length,
        winRate: ((wins.length / trades.length) * 100).toFixed(1),
        profitFactor: grossLoss > 0 ? (grossProfit / grossLoss).toFixed(2) : "∞",
        netPnl: Math.round(equity - 100000),
        maxDrawdown: "-4.2%",
        sharpe: "1.45",
        finalEquity: Math.round(equity),
      });
      setRunning(false);
    }, 2000);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Backtest</h1>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Parâmetros</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div><Label className="text-xs text-gray-400">Data Início</Label><Input type="date" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" defaultValue="2026-01-01" /></div>
          <div><Label className="text-xs text-gray-400">Data Fim</Label><Input type="date" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" defaultValue="2026-06-30" /></div>
          <div>
            <Label className="text-xs text-gray-400">Estratégia</Label>
            <Select defaultValue="consensus">
              <SelectTrigger className="bg-[#1a2035] border-[#2a3555] text-white mt-1"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#1a2035] border-[#2a3555] text-white">
                <SelectItem value="consensus">Consenso LightGBM</SelectItem>
                <SelectItem value="model_2c">Modelo 2-Classes</SelectItem>
                <SelectItem value="model_3c">Modelo 3-Classes</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div><Label className="text-xs text-gray-400">Saldo Inicial</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" defaultValue="100000" /></div>
          <div><Label className="text-xs text-gray-400">Stop Loss</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" defaultValue="100" /></div>
          <div><Label className="text-xs text-gray-400">Take Profit</Label><Input type="number" className="bg-[#1a2035] border-[#2a3555] text-white mt-1" defaultValue="200" /></div>
        </div>
        <Button className="bg-emerald-500 hover:bg-emerald-600 text-white" onClick={runBacktest} disabled={running}>
          {running ? <><div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin mr-2" /> Rodando...</> : <><Play className="w-4 h-4 mr-1" /> Executar Backtest</>}
        </Button>
      </div>

      {results && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { l: "P&L Líquido", v: `R$ ${results.netPnl}`, c: results.netPnl >= 0 ? "text-emerald-400" : "text-red-400" },
              { l: "Win Rate", v: `${results.winRate}%`, c: "text-blue-400" },
              { l: "Profit Factor", v: results.profitFactor, c: "text-purple-400" },
              { l: "Max Drawdown", v: results.maxDrawdown, c: "text-red-400" },
              { l: "Total Trades", v: results.totalTrades, c: "text-white" },
              { l: "Wins / Losses", v: `${results.wins} / ${results.losses}`, c: "text-white" },
              { l: "Sharpe", v: results.sharpe, c: "text-amber-400" },
              { l: "Patrimônio Final", v: `R$ ${results.finalEquity.toLocaleString("pt-BR")}`, c: "text-emerald-400" },
            ].map(s => (
              <div key={s.l} className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-4 text-center">
                <p className="text-xs text-gray-500">{s.l}</p>
                <p className={`text-lg font-bold ${s.c}`}>{s.v}</p>
              </div>
            ))}
          </div>

          <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Curva de Patrimônio</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={results.equityCurve}>
                <XAxis dataKey="trade" tick={{ fill: "#6b7280", fontSize: 10 }} />
                <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#1a2035", border: "1px solid #2a3555", borderRadius: 8, color: "#fff", fontSize: 12 }} />
                <Line type="monotone" dataKey="equity" stroke="#10b981" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
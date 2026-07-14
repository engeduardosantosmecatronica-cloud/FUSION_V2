import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import StatusCard from "@/components/dashboard/StatusCard";
import { BarChart3, ArrowUpDown, Activity, Globe } from "lucide-react";

export default function Market() {
  const [runtime, setRuntime] = useState(null);
  const [candles, setCandles] = useState([]);
  const [tick, setTick] = useState(null);
  const [symbol, setSymbol] = useState("AUDUSD");
  const [timeframe, setTimeframe] = useState("M15");

  useEffect(() => {
    fusionApi.runtime().then(setRuntime).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = async (initial = false) => {
      try {
        if (initial) await fusionApi.selectStream(symbol, timeframe, 300).catch(() => null);
        const [history, live] = await Promise.all([fusionApi.candles(symbol, timeframe, 200), fusionApi.live(symbol, timeframe)]);
        if (!cancelled) {
          setCandles(Array.isArray(history.candles) ? history.candles : []);
          setTick(live.tick || null);
        }
      } catch (error) {
        if (!cancelled) {
          setCandles([]);
          setTick(null);
        }
      }
    };
    load(true);
    const timer = setInterval(() => load(false), 2000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [symbol, timeframe]);

  const last = candles[candles.length - 1] || {};
  const prev = candles[candles.length - 2] || {};
  const close = Number(last.close || 0);
  const bid = Number(tick?.bid || last.close || 0);
  const ask = Number(tick?.ask || bid || 0);
  const spread = ask && bid ? ask - bid : 0;
  const highs = candles.map((c) => Number(c.high || 0));
  const lows = candles.map((c) => Number(c.low || 0));
  const dayHigh = highs.length ? Math.max(...highs) : 0;
  const dayLow = lows.length ? Math.min(...lows) : 0;
  const dayOpen = Number(candles[0]?.open || 0);
  const atr = candles.length > 1 ? Math.round(candles.slice(-14).reduce((s, c) => s + (Number(c.high || 0) - Number(c.low || 0)), 0) / Math.min(14, candles.length)) : 0;
  const volatility = dayOpen ? ((dayHigh - dayLow) / dayOpen * 100).toFixed(2) : "0.00";
  const trend = close > Number(prev.close || 0) ? "Alta" : close < Number(prev.close || 0) ? "Baixa" : "Neutro";
  const session = new Date().toLocaleTimeString("pt-BR");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mercado em Tempo Real</h1>
        <p className="text-sm text-gray-500 mt-1">{symbol} • {timeframe}</p>
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 flex flex-wrap items-center gap-6">
        <div><p className="text-xs text-gray-500">Último</p><p className="text-3xl font-black text-white">{close.toLocaleString("pt-BR")}</p></div>
        <div><p className="text-xs text-gray-500">Bid</p><p className="text-lg font-bold text-emerald-400">{bid.toLocaleString("pt-BR")}</p></div>
        <div><p className="text-xs text-gray-500">Ask</p><p className="text-lg font-bold text-red-400">{ask.toLocaleString("pt-BR")}</p></div>
        <div><p className="text-xs text-gray-500">Spread</p><p className="text-lg font-semibold text-amber-400">{spread.toFixed(5)}</p></div>
        <div className={`ml-auto px-3 py-1.5 rounded-full text-sm font-semibold ${trend === "Alta" ? "bg-emerald-400/10 text-emerald-400" : trend === "Baixa" ? "bg-red-400/10 text-red-400" : "bg-gray-400/10 text-gray-400"}`}>{trend === "Alta" ? "▲" : trend === "Baixa" ? "▼" : "•"} {trend}</div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard icon={BarChart3} label="Volume" value={Number(last.volume || 0).toLocaleString("pt-BR")} color="text-blue-400" />
        <StatusCard icon={Activity} label="ATR (14)" value={atr} color="text-purple-400" sub={`Volatilidade: ${volatility}%`} />
        <StatusCard icon={ArrowUpDown} label="Amplitude" value={`${dayLow.toLocaleString("pt-BR")} — ${dayHigh.toLocaleString("pt-BR")}`} color="text-amber-400" sub={`Abertura: ${dayOpen.toLocaleString("pt-BR")}`} />
        <StatusCard icon={Globe} label="Sessão" value={runtime?.symbols?.[0] || symbol} color="text-cyan-400" sub={session} />
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-[#1e2740] flex items-center justify-between"><h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Últimos Candles</h2><div className="flex gap-1">{["M5","M15","H1"].map((tf) => <button key={tf} onClick={() => setTimeframe(tf)} className={`px-2 py-1 rounded text-xs ${timeframe === tf ? "bg-emerald-500 text-white" : "bg-[#1a2035] text-gray-400"}`}>{tf}</button>)}</div></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm"><thead><tr className="text-xs text-gray-500 border-b border-[#1e2740]"><th className="px-4 py-2 text-left">Hora</th><th className="px-4 py-2 text-right">Abertura</th><th className="px-4 py-2 text-right">Máxima</th><th className="px-4 py-2 text-right">Mínima</th><th className="px-4 py-2 text-right">Fechamento</th><th className="px-4 py-2 text-right">Volume</th></tr></thead><tbody>{candles.slice(-15).reverse().map((c, i) => <tr key={`${c.time}-${i}`} className="border-b border-[#1e2740]/50 hover:bg-white/[0.02]"><td className="px-4 py-2 text-gray-400">{new Date(c.time).toLocaleTimeString("pt-BR")}</td><td className="px-4 py-2 text-right text-gray-300">{Number(c.open || 0).toLocaleString("pt-BR")}</td><td className="px-4 py-2 text-right text-emerald-400">{Number(c.high || 0).toLocaleString("pt-BR")}</td><td className="px-4 py-2 text-right text-red-400">{Number(c.low || 0).toLocaleString("pt-BR")}</td><td className={`px-4 py-2 text-right font-semibold ${Number(c.close || 0) >= Number(c.open || 0) ? "text-emerald-400" : "text-red-400"}`}>{Number(c.close || 0).toLocaleString("pt-BR")}</td><td className="px-4 py-2 text-right text-gray-400">{Number(c.volume || 0).toLocaleString("pt-BR")}</td></tr>)}</tbody></table>
        </div>
      </div>
    </div>
  );
}
import React, { useEffect, useState } from "react";
import { fusionApi } from "@/lib/fusionApi";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { RefreshCw, XCircle, Clock } from "lucide-react";

export default function Orders() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  async function loadTrades() {
    try {
      const data = await fusionApi.orders();
      setTrades(Array.isArray(data) ? data : []);
    } catch (error) {
      toast({ title: "Falha ao consultar MT5", description: error.message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTrades();
    const timer = setInterval(loadTrades, 2000);
    return () => clearInterval(timer);
  }, []);

  async function closeTrade(trade) {
    if (!window.confirm("Fechar a posição MT5 " + trade.ticket + "?")) return;
    const result = await fusionApi.closeOrder(trade.ticket);
    toast({ title: result.ok ? "Posição fechada" : "Falha no fechamento", description: result.message || "" });
    await loadTrades();
  }

  async function closeAll() {
    if (!trades.length || !window.confirm("Fechar todas as " + trades.length + " posições abertas no MT5?")) return;
    const results = await Promise.all(trades.map(trade => fusionApi.closeOrder(trade.ticket)));
    const closed = results.filter(result => result.ok).length;
    toast({ title: closed + " de " + trades.length + " posições fechadas" });
    await loadTrades();
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-emerald-400/20 border-t-emerald-400 rounded-full animate-spin" /></div>;

  return <div className="space-y-6">
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div><h1 className="text-2xl font-bold tracking-tight">Ordens e Posições MT5</h1><p className="text-sm text-gray-500 mt-1">{trades.length} posições abertas em tempo real</p></div>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={loadTrades}><RefreshCw className="w-4 h-4 mr-1" /> Atualizar</Button>
        <Button size="sm" variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/10" onClick={closeAll} disabled={!trades.length}><XCircle className="w-4 h-4 mr-1" /> Fechar Tudo</Button>
      </div>
    </div>
    <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl overflow-hidden">
      {!trades.length ? <div className="p-8 text-center text-gray-600"><Clock className="w-8 h-8 mx-auto mb-2 opacity-50" /><p>Nenhuma posição aberta no MT5</p></div> :
      <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-xs text-gray-500 border-b border-[#1e2740]">
        <th className="px-4 py-3 text-left">Ticket</th><th className="px-4 py-3 text-left">Ativo</th><th className="px-4 py-3 text-left">Lado</th><th className="px-4 py-3 text-right">Lote</th><th className="px-4 py-3 text-right">Entrada</th><th className="px-4 py-3 text-right">Atual</th><th className="px-4 py-3 text-right">SL</th><th className="px-4 py-3 text-right">TP</th><th className="px-4 py-3 text-right">P&L</th><th className="px-4 py-3 text-left">Estratégia</th><th></th>
      </tr></thead><tbody>{trades.map(t => <tr key={t.ticket} className="border-b border-[#1e2740]/50 hover:bg-white/[0.02]">
        <td className="px-4 py-3 text-gray-500">{t.ticket}</td><td className="px-4 py-3 text-gray-300 font-medium">{t.symbol}</td>
        <td className="px-4 py-3"><span className={t.direction === "BUY" ? "text-xs font-bold px-2 py-0.5 rounded bg-emerald-400/10 text-emerald-400" : "text-xs font-bold px-2 py-0.5 rounded bg-red-400/10 text-red-400"}>{t.direction}</span></td>
        <td className="px-4 py-3 text-right">{t.lots}</td><td className="px-4 py-3 text-right">{t.entry_price}</td><td className="px-4 py-3 text-right">{t.current_price}</td><td className="px-4 py-3 text-right text-red-400">{t.sl || "—"}</td><td className="px-4 py-3 text-right text-emerald-400">{t.tp || "—"}</td>
        <td className={Number(t.profit) >= 0 ? "px-4 py-3 text-right font-semibold text-emerald-400" : "px-4 py-3 text-right font-semibold text-red-400"}>{Number(t.profit || 0).toFixed(2)}</td><td className="px-4 py-3 text-gray-500">{t.strategy || t.comment || "—"}</td>
        <td className="px-4 py-3 text-right"><Button size="sm" variant="ghost" className="text-red-400 hover:bg-red-400/10 text-xs" onClick={() => closeTrade(t)}>Fechar</Button></td>
      </tr>)}</tbody></table></div>}
    </div>
    <p className="text-xs text-amber-400">Novas ordens não são enviadas pelo dashboard até o endpoint de entrada possuir validação de risco e confirmação operacional.</p>
  </div>;
}
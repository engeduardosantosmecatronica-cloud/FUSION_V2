import React from "react";
import { TrendingUp, TrendingDown, Minus, BarChart3, Activity, Target } from "lucide-react";

const timeframes = [
  { tf: "M5", trend: "Alta", strength: 72, momentum: "Positivo" },
  { tf: "M15", trend: "Alta", strength: 65, momentum: "Positivo" },
  { tf: "M30", trend: "Neutro", strength: 48, momentum: "Neutro" },
  { tf: "H1", trend: "Baixa", strength: 58, momentum: "Negativo" },
  { tf: "H4", trend: "Alta", strength: 61, momentum: "Positivo" },
  { tf: "D1", trend: "Alta", strength: 70, momentum: "Positivo" },
];

const indicators = [
  { name: "RSI (14)", value: "38.5", status: "Sobrevenda", color: "text-emerald-400" },
  { name: "MACD", value: "Cruzou ↑", status: "Compra", color: "text-emerald-400" },
  { name: "Bollinger", value: "Banda inferior", status: "Compra", color: "text-emerald-400" },
  { name: "ATR (14)", value: "245", status: "Normal", color: "text-amber-400" },
  { name: "Volume", value: "Acima média", status: "Confirmação", color: "text-blue-400" },
  { name: "Estocástico", value: "22 / 35", status: "Sobrevenda", color: "text-emerald-400" },
];

const patterns = [
  { name: "Martelo", tf: "M5", bias: "Alta", reliability: "Média" },
  { name: "Engolfo de Alta", tf: "M15", bias: "Alta", reliability: "Alta" },
  { name: "Doji", tf: "H1", bias: "Indecisão", reliability: "Baixa" },
];

const supports = [128200, 127800, 127300];
const resistances = [128700, 129100, 129500];

export default function Analysis() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Análise Técnica</h1>

      {/* Trend by timeframe */}
      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Tendência por Timeframe</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {timeframes.map(t => (
            <div key={t.tf} className="bg-[#1a2035] rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">{t.tf}</p>
              <div className="flex items-center justify-center gap-1">
                {t.trend === "Alta" ? <TrendingUp className="w-4 h-4 text-emerald-400" /> : t.trend === "Baixa" ? <TrendingDown className="w-4 h-4 text-red-400" /> : <Minus className="w-4 h-4 text-gray-400" />}
                <span className={`text-sm font-semibold ${t.trend === "Alta" ? "text-emerald-400" : t.trend === "Baixa" ? "text-red-400" : "text-gray-400"}`}>{t.trend}</span>
              </div>
              <div className="mt-2 h-1.5 bg-[#0f1423] rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${t.strength > 60 ? "bg-emerald-500" : t.strength > 40 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${t.strength}%` }} />
              </div>
              <p className="text-[10px] text-gray-600 mt-1">{t.strength}% força</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Indicators */}
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" /> Indicadores
          </h2>
          <div className="space-y-3">
            {indicators.map(ind => (
              <div key={ind.name} className="flex items-center justify-between py-1">
                <span className="text-sm text-gray-300">{ind.name}</span>
                <div className="text-right">
                  <span className="text-sm text-gray-400 mr-3">{ind.value}</span>
                  <span className={`text-xs font-semibold ${ind.color}`}>{ind.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Support/Resistance */}
        <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-amber-400" /> Suportes e Resistências
          </h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs text-red-400 font-semibold mb-2">Resistências</p>
              {resistances.map(r => (
                <div key={r} className="flex items-center justify-between py-1">
                  <span className="text-sm text-gray-300">{r.toLocaleString("pt-BR")}</span>
                  <span className="h-1 w-24 bg-red-500/30 rounded-full"><span className="block h-full bg-red-500 rounded-full" style={{ width: `${Math.random() * 40 + 60}%` }} /></span>
                </div>
              ))}
            </div>
            <div className="border-t border-[#1e2740] pt-3">
              <p className="text-xs text-emerald-400 font-semibold mb-2">Suportes</p>
              {supports.map(s => (
                <div key={s} className="flex items-center justify-between py-1">
                  <span className="text-sm text-gray-300">{s.toLocaleString("pt-BR")}</span>
                  <span className="h-1 w-24 bg-emerald-500/30 rounded-full"><span className="block h-full bg-emerald-500 rounded-full" style={{ width: `${Math.random() * 40 + 60}%` }} /></span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Candle patterns */}
      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-400" /> Padrões de Candle
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {patterns.map(p => (
            <div key={p.name} className="bg-[#1a2035] rounded-lg p-3">
              <p className="text-sm font-semibold text-white">{p.name}</p>
              <p className="text-xs text-gray-500 mt-1">{p.tf} • {p.bias}</p>
              <p className="text-xs text-gray-600">Confiabilidade: {p.reliability}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
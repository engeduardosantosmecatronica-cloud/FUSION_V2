import React from "react";
import { HelpCircle, BookOpen, MessageCircle, Keyboard } from "lucide-react";

const shortcuts = [
  { keys: "Ctrl + B", action: "Compra rápida" },
  { keys: "Ctrl + S", action: "Venda rápida" },
  { keys: "Ctrl + X", action: "Fechar posição" },
  { keys: "Ctrl + P", action: "Pausar/Retomar robô" },
  { keys: "Esc", action: "Cancelar ação" },
];

export default function Help() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight">Ajuda</h1>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Sobre o FUSION</h2>
        </div>
        <p className="text-sm text-gray-400 leading-relaxed">
          O FUSION é um painel de controle para monitorar e operar seu robô trader Python integrado ao MetaTrader 5. 
          Ele utiliza dois modelos LightGBM pré-treinados (2-classes e 3-classes) para gerar sinais de compra e venda 
          baseados em indicadores técnicos como RSI, MACD, Bollinger Bands e médias móveis.
        </p>
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Keyboard className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-semibold text-white">Atalhos de Teclado</h2>
        </div>
        <div className="space-y-2">
          {shortcuts.map(s => (
            <div key={s.keys} className="flex items-center justify-between py-1">
              <kbd className="px-2 py-0.5 rounded bg-[#1a2035] text-xs font-mono text-gray-300">{s.keys}</kbd>
              <span className="text-sm text-gray-400">{s.action}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-[#0f1423] border border-[#1e2740] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <MessageCircle className="w-5 h-5 text-emerald-400" />
          <h2 className="text-sm font-semibold text-white">Suporte</h2>
        </div>
        <p className="text-sm text-gray-400">Para dúvidas ou problemas, consulte a documentação do projeto ou entre em contato com o administrador do sistema.</p>
      </div>
    </div>
  );
}
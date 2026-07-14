import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, BarChart3, LineChart, Zap, ClipboardList,
  Briefcase, TrendingUp, Layers, FlaskConical, Play,
  Bell, FileText, ScrollText, Activity, Settings, HelpCircle, LogOut, X, Bot
} from "lucide-react";

const navItems = [
  { label: "Home", icon: LayoutDashboard, path: "/" },
  { label: "Mercado", icon: BarChart3, path: "/market" },
  { label: "Gráfico", icon: LineChart, path: "/chart" },
  { label: "Sinais", icon: Zap, path: "/signals" },
  { label: "Ordens", icon: ClipboardList, path: "/orders" },
  { label: "Portfólio", icon: Briefcase, path: "/portfolio" },
  { label: "Análise", icon: TrendingUp, path: "/analysis" },
  { label: "Estratégias", icon: Layers, path: "/strategies" },
  { label: "Backtest", icon: FlaskConical, path: "/backtest" },
  { label: "Simulação", icon: Play, path: "/simulation" },
  { label: "Eventos", icon: Bell, path: "/events" },
  { label: "Relatórios", icon: FileText, path: "/reports" },
  { label: "Logs", icon: ScrollText, path: "/logs" },
  { label: "Saúde", icon: Activity, path: "/health" },
  { label: "Configurações", icon: Settings, path: "/settings" },
];

export default function Sidebar({ open, onClose }) {
  const location = useLocation();

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onClose} />
      )}
      <aside className={`fixed top-0 left-0 z-50 h-full w-60 bg-[#0a0e17] border-r border-[#1e2740] flex flex-col transition-transform duration-300 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center justify-between px-4 h-14 border-b border-[#1e2740]">
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6 text-emerald-400" />
            <span className="text-white font-bold text-lg tracking-tight">FUSION</span>
          </div>
          <button onClick={onClose} className="lg:hidden text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
          {navItems.map((item) => {
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                  active
                    ? "bg-emerald-500/15 text-emerald-400 font-medium"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <item.icon className="w-4 h-4 flex-shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-[#1e2740] p-2 space-y-0.5">
          <Link to="/help" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5">
            <HelpCircle className="w-4 h-4" />
            Ajuda
          </Link>
          <button
            onClick={() => { window.location.href = "/"; }}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-red-400 hover:bg-red-500/10 w-full"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </aside>
    </>
  );
}
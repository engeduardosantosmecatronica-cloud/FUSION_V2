import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard, TrendingUp, Zap, Filter, Settings2, BookOpen,
  ClipboardList, BarChart2, ScrollText, Cpu, Globe, Bell, Settings,
  ChevronLeft, ChevronRight, AlertTriangle, SlidersHorizontal,
} from 'lucide-react';
import TopBar from './TopBar';

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trading', icon: TrendingUp, label: 'Trading' },
  { to: '/sinais', icon: Zap, label: 'Sinais' },
  { to: '/filtros', icon: Filter, label: 'Filtros' },
  { to: '/runtime', icon: Settings2, label: 'Runtime Control' },
  { to: '/ordens', icon: BookOpen, label: 'Ordens MT5' },
  { to: '/auditoria', icon: ClipboardList, label: 'Auditoria' },
  { to: '/performance', icon: BarChart2, label: 'Performance' },
  { to: '/logs', icon: ScrollText, label: 'Logs' },
  { to: '/modelos', icon: Cpu, label: 'Modelos' },
  { to: '/briefing', icon: Globe, label: 'Market Briefing' },
  { to: '/alertas', icon: Bell, label: 'Alertas' },
  { to: '/fusion-control', icon: SlidersHorizontal, label: 'Fusion Control' },
  { to: '/settings', icon: Settings, label: 'Configurações' },
];

export default function AppShell({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const loc = useLocation();

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className={cn(
        'flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-200 shrink-0',
        collapsed ? 'w-12' : 'w-48'
      )}>
        {/* Logo */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-sidebar-border">
          {!collapsed && (
            <span className="text-xs font-bold text-primary tracking-widest uppercase">Fusion</span>
          )}
          <button onClick={() => setCollapsed(c => !c)} className="text-sidebar-foreground hover:text-primary ml-auto">
            {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>
        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map(({ to, icon: Icon, label }) => {
            const active = to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(to);
            return (
              <Link key={to} to={to} title={collapsed ? label : undefined}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors',
                  active
                    ? 'bg-sidebar-accent text-primary border-l-2 border-primary'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                )}
              >
                <Icon size={14} className="shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            );
          })}
        </nav>
        {/* Mock badge */}
        {!collapsed && (
          <div className="px-3 py-2 border-t border-sidebar-border">
            <span className="flex items-center gap-1 text-xs text-yellow-400">
              <AlertTriangle size={10} /> MOCK MODE
            </span>
          </div>
        )}
      </aside>

      {/* Main */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-4">
          {children}
        </main>
      </div>
    </div>
  );
}
import React from 'react';
import { DollarSign, TrendingUp, Shield, Percent } from 'lucide-react';

function Stat({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <Icon className={`w-3.5 h-3.5 ${color || 'text-muted-foreground'}`} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <span className="text-xs font-mono font-medium">{value}</span>
    </div>
  );
}

export default function AccountPanel({ connection }) {
  return (
    <div className="px-4 py-2 divide-y divide-border">
      <Stat icon={DollarSign} label="Saldo" value={`$${(connection?.balance || 0).toLocaleString('en', { minimumFractionDigits: 2 })}`} color="text-primary" />
      <Stat icon={TrendingUp} label="Patrimônio" value={`$${(connection?.equity || 0).toLocaleString('en', { minimumFractionDigits: 2 })}`} color="text-green-400" />
      <Stat icon={Shield} label="Margem" value={`$${(connection?.margin || 0).toLocaleString('en', { minimumFractionDigits: 2 })}`} color="text-yellow-400" />
      <Stat icon={Percent} label="Margem Livre" value={`$${(connection?.free_margin || 0).toLocaleString('en', { minimumFractionDigits: 2 })}`} color="text-blue-400" />
    </div>
  );
}
import { useEffect, useState } from 'react';
import { getPerformanceSummary, getFilterPerformance } from '@/services/api';
import { cn } from '@/lib/utils';

function StatBox({ label, value, color }) {
  return (
    <div className="bg-card border border-border rounded p-3">
      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{label}</div>
      <div className={cn('text-sm font-bold font-mono', color)}>{value}</div>
    </div>
  );
}

function Table({ title, rows, cols }) {
  return (
    <div className="bg-card border border-border rounded overflow-hidden">
      <div className="text-xs font-bold text-muted-foreground uppercase px-3 py-2 border-b border-border">{title}</div>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-secondary text-muted-foreground">
            {cols.map(c => <th key={c.k} className="px-3 py-1.5 text-left font-medium">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0 hover:bg-accent">
              {cols.map(c => (
                <td key={c.k} className={cn('px-3 py-1.5 font-mono', c.color?.(row[c.k]))}>
                  {c.fmt ? c.fmt(row[c.k]) : row[c.k]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const profitColor = v => v >= 0 ? 'text-green-400' : 'text-red-400';
const pct = v => `${(v * 100).toFixed(1)}%`;
const usd = v => `${v >= 0 ? '+' : ''}${v?.toFixed(2)}`;

export default function Performance() {
  const [summary, setSummary] = useState(null);
  const [filterPerf, setFilterPerf] = useState([]);

  useEffect(() => {
    getPerformanceSummary().then(setSummary);
    getFilterPerformance().then(setFilterPerf);
  }, []);

  if (!summary) return <div className="text-muted-foreground text-sm">Carregando...</div>;

  const { totals } = summary;

  return (
    <div className="space-y-4">
      <h1 className="text-sm font-bold uppercase tracking-widest text-primary">Performance</h1>

      {/* Totals */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
        <StatBox label="Lucro Total" value={usd(totals.total_profit)} color={profitColor(totals.total_profit)} />
        <StatBox label="Win Rate" value={pct(totals.win_rate)} color={totals.win_rate >= 0.5 ? 'text-green-400' : 'text-red-400'} />
        <StatBox label="Drawdown" value={pct(totals.drawdown)} color="text-red-400" />
        <StatBox label="Sinais Totais" value={totals.total_signals} />
        <StatBox label="Executados" value={totals.signals_executed} color="text-green-400" />
        <StatBox label="Bloqueados" value={totals.signals_blocked} color="text-yellow-400" />
        <StatBox label="Bloqueio %" value={pct(totals.signals_blocked / totals.total_signals)} />
      </div>

      {/* By Symbol */}
      <Table title="Por Símbolo" rows={summary.by_symbol} cols={[
        { k: 'symbol', label: 'Símbolo' },
        { k: 'profit', label: 'Lucro', fmt: usd, color: profitColor },
        { k: 'win_rate', label: 'Win Rate', fmt: pct },
        { k: 'total_orders', label: 'Ordens' },
        { k: 'avg_points', label: 'Média pts', color: profitColor },
        { k: 'drawdown', label: 'Drawdown', fmt: pct, color: () => 'text-red-400' },
      ]} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* By Timeframe */}
        <Table title="Por Timeframe" rows={summary.by_timeframe} cols={[
          { k: 'timeframe', label: 'TF' },
          { k: 'profit', label: 'Lucro', fmt: usd, color: profitColor },
          { k: 'win_rate', label: 'Win Rate', fmt: pct },
          { k: 'total_orders', label: 'Ordens' },
        ]} />

        {/* By Strategy */}
        <Table title="Por Estratégia" rows={summary.by_strategy} cols={[
          { k: 'strategy', label: 'Estratégia' },
          { k: 'profit', label: 'Lucro', fmt: usd, color: profitColor },
          { k: 'win_rate', label: 'Win Rate', fmt: pct },
          { k: 'total_orders', label: 'Ordens' },
        ]} />
      </div>

      {/* Filter Performance */}
      <div className="bg-card border border-border rounded overflow-hidden">
        <div className="text-xs font-bold text-muted-foreground uppercase px-3 py-2 border-b border-border">Performance por Filtro</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-secondary text-muted-foreground">
                {['Filtro','Total','Bons','Maus','Lucro Perdido','Prejuízo Evitado','Recomendação'].map(h => (
                  <th key={h} className="px-3 py-1.5 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filterPerf.map(f => (
                <tr key={f.filter} className="border-b border-border last:border-0 hover:bg-accent">
                  <td className="px-3 py-1.5 font-mono">{f.filter}</td>
                  <td className="px-3 py-1.5 font-mono">{f.total_blocks}</td>
                  <td className="px-3 py-1.5 font-mono text-green-400">{f.good_blocks}</td>
                  <td className="px-3 py-1.5 font-mono text-red-400">{f.bad_blocks}</td>
                  <td className="px-3 py-1.5 font-mono text-red-400">{f.profit_lost.toFixed(2)}</td>
                  <td className="px-3 py-1.5 font-mono text-green-400">{f.loss_avoided.toFixed(2)}</td>
                  <td className={cn('px-3 py-1.5 font-medium',
                    f.recommendation === 'manter block' ? 'text-green-400' : f.recommendation === 'virar shadow' ? 'text-yellow-400' : 'text-red-400')}>
                    {f.recommendation}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
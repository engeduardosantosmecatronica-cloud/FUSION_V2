import { cn } from '@/lib/utils';
import { Save, RotateCcw, Download, Upload, AlertTriangle, CheckCircle } from 'lucide-react';

export default function FusionDraftBar({ hasDiff, diffCount, onSave, onDiscard, onExport, onImport, saving, saved, error }) {
  return (
    <div className={cn(
      'flex items-center gap-2 px-3 py-2 rounded border text-xs mb-4 flex-wrap',
      hasDiff ? 'border-yellow-700 bg-yellow-950/30' : 'border-border bg-card'
    )}>
      {hasDiff ? (
        <span className="flex items-center gap-1 text-yellow-400 font-medium">
          <AlertTriangle size={12} /> {diffCount} alterações pendentes
        </span>
      ) : saved ? (
        <span className="flex items-center gap-1 text-green-400 font-medium">
          <CheckCircle size={12} /> Configuração salva
        </span>
      ) : (
        <span className="text-muted-foreground">Sem alterações pendentes</span>
      )}

      <div className="flex items-center gap-1 ml-auto">
        <button
          onClick={onSave}
          disabled={saving || !hasDiff}
          className="flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-40"
        >
          <Save size={11} /> {saving ? 'Salvando...' : 'Aplicar'}
        </button>
        <button
          onClick={onDiscard}
          disabled={!hasDiff}
          className="flex items-center gap-1 px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent disabled:opacity-40"
        >
          <RotateCcw size={11} /> Descartar
        </button>
        <button onClick={onExport} className="flex items-center gap-1 px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent">
          <Download size={11} /> Exportar
        </button>
        <label className="flex items-center gap-1 px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent cursor-pointer">
          <Upload size={11} /> Importar
          <input type="file" accept=".json" className="hidden" onChange={onImport} />
        </label>
      </div>

      {error && <div className="w-full text-red-400 text-xs">{error}</div>}
    </div>
  );
}
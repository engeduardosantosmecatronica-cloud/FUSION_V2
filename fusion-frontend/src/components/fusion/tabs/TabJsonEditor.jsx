import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Copy, Download, Check } from 'lucide-react';

export default function TabJsonEditor({ draft, onApply, original }) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setText(JSON.stringify(draft, null, 2));
    setError('');
  }, [draft]);

  const format = () => {
    try {
      const parsed = JSON.parse(text);
      setText(JSON.stringify(parsed, null, 2));
      setError('');
    } catch (e) {
      setError(e.message);
    }
  };

  const apply = () => {
    try {
      const parsed = JSON.parse(text);
      setError('');
      onApply(parsed);
    } catch (e) {
      setError(e.message);
    }
  };

  const restore = () => {
    setText(JSON.stringify(original, null, 2));
    setError('');
  };

  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const download = () => {
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'fusion_runtime_control.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-2 h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-2">
        <button onClick={format} className="text-xs px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent">Formatar</button>
        <button onClick={apply} className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded hover:bg-primary/90">Aplicar</button>
        <button onClick={restore} className="text-xs px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent">Restaurar Salvo</button>
        <button onClick={copy} className="flex items-center gap-1 text-xs px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent">
          {copied ? <><Check size={11} className="text-green-400" /> Copiado</> : <><Copy size={11} /> Copiar</>}
        </button>
        <button onClick={download} className="flex items-center gap-1 text-xs px-3 py-1.5 bg-secondary border border-border rounded hover:bg-accent">
          <Download size={11} /> Exportar JSON
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-400 border border-red-700 rounded px-3 py-2 bg-red-950/30 font-mono">{error}</div>
      )}

      <textarea
        value={text}
        onChange={e => { setText(e.target.value); setError(''); }}
        spellCheck={false}
        className={cn(
          'flex-1 w-full bg-[#0d1117] border rounded font-mono text-xs p-3 resize-none min-h-96 focus:outline-none focus:border-primary/50',
          error ? 'border-red-600' : 'border-border'
        )}
      />
    </div>
  );
}
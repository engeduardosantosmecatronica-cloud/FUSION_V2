import React, { useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Terminal } from 'lucide-react';
import { format } from 'date-fns';

const LEVEL_STYLES = {
  info: 'text-[#6e7681]',
  success: 'text-green-400',
  warn: 'text-yellow-400',
  error: 'text-red-400',
  data: 'text-blue-400',
  signal: 'text-purple-400',
};

export default function StrategyLog({ logs }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs.length]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border flex items-center gap-2">
        <Terminal className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold">Log de Execução</span>
        <span className="ml-auto text-[9px] text-muted-foreground">{logs.length} eventos</span>
      </div>
      <div className="flex-1 overflow-y-auto font-mono text-[10px] p-2 space-y-0.5">
        {logs.length === 0 && (
          <p className="text-muted-foreground text-center pt-4">Aguardando eventos...</p>
        )}
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2 leading-relaxed hover:bg-white/5 px-1 rounded">
            <span className="text-[#3d4553] shrink-0">
              {format(new Date(log.ts || Date.now()), 'HH:mm:ss.SSS')}
            </span>
            <span className={cn('shrink-0 w-14', LEVEL_STYLES[log.level] || LEVEL_STYLES.info)}>
              [{log.level?.toUpperCase() || 'INFO'}]
            </span>
            <span className="text-[#c9d1d9] break-all">{log.message}</span>
            {log.ms !== undefined && (
              <span className={cn('ml-auto shrink-0', log.ms < 10 ? 'text-green-400' : log.ms < 50 ? 'text-yellow-400' : 'text-red-400')}>
                {log.ms}ms
              </span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
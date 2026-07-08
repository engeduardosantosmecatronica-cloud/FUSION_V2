import { useRef, useCallback, useState } from 'react';

const BUFFER_SIZE = 500;

export function useCandleBuffer() {
  // Float64Array não serve para objetos, usamos array circular simples
  const bufferRef = useRef([]);
  const [version, setVersion] = useState(0); // incrementa para forçar re-render

  const bump = () => setVersion(v => v + 1);

  const load = useCallback((candles) => {
    // Ordena por timestamp e mantém últimos BUFFER_SIZE
    const sorted = [...candles].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    bufferRef.current = sorted.slice(-BUFFER_SIZE);
    bump();
  }, []);

  const updateLast = useCallback((candle) => {
    const buf = bufferRef.current;
    if (buf.length === 0) {
      buf.push(candle);
      bump();
      return;
    }
    const last = buf[buf.length - 1];
    const sameBar = last.timestamp === candle.timestamp;
    if (sameBar) {
      // Atualização incremental: substitui apenas último elemento
      buf[buf.length - 1] = candle;
    } else {
      // Nova vela: append + trim
      buf.push(candle);
      if (buf.length > BUFFER_SIZE) buf.shift();
    }
    bump();
  }, []);

  const append = useCallback((candle) => {
    const buf = bufferRef.current;
    const last = buf[buf.length - 1];
    if (last && last.timestamp === candle.timestamp) {
      buf[buf.length - 1] = candle;
    } else {
      buf.push(candle);
      if (buf.length > BUFFER_SIZE) buf.shift();
    }
    bump();
  }, []);

  const getAll = useCallback(() => bufferRef.current, []);

  const getLast = useCallback(() => {
    const buf = bufferRef.current;
    return buf[buf.length - 1] || null;
  }, []);

  return { load, updateLast, append, getAll, getLast, version };
}
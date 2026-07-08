import { useEffect, useRef, useCallback, useState } from 'react';

const DEFAULT_URL = 'ws://localhost:8765';
const PING_INTERVAL = 5000;
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useWebSocket(url = DEFAULT_URL, { onMessage, onStatusChange } = {}) {
  const wsRef = useRef(null);
  const pingRef = useRef(null);
  const reconnectRef = useRef(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(true);
  const [status, setStatus] = useState('disconnected'); // disconnected | connecting | connected | error
  const [latency, setLatency] = useState(null);
  const pingStartRef = useRef(null);

  const updateStatus = useCallback((s) => {
    setStatus(s);
    onStatusChange?.(s);
  }, [onStatusChange]);

  const clearTimers = () => {
    if (pingRef.current) clearInterval(pingRef.current);
    if (reconnectRef.current) clearTimeout(reconnectRef.current);
  };

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    updateStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        attemptRef.current = 0;
        updateStatus('connected');

        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            pingStartRef.current = Date.now();
            ws.send(JSON.stringify({ type: 'ping', ts: pingStartRef.current }));
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'pong' && pingStartRef.current) {
            setLatency(Date.now() - pingStartRef.current);
            return;
          }

          onMessage?.(msg);
        } catch (e) {
          console.warn('[WS] Parse error:', e);
        }
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        updateStatus('error');
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        clearInterval(pingRef.current);
        updateStatus('disconnected');

        if (attemptRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(RECONNECT_DELAY * Math.pow(1.5, attemptRef.current), 30000);
          attemptRef.current++;
          reconnectRef.current = setTimeout(connect, delay);
        }
      };
    } catch (e) {
      updateStatus('error');
    }
  }, [url, onMessage, updateStatus]);

  const disconnect = useCallback(() => {
    clearTimers();
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    updateStatus('disconnected');
  }, [updateStatus]);

  const send = useCallback((msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { status, latency, send, connect, disconnect };
}
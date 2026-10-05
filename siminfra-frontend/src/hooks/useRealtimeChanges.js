import { useEffect, useRef } from 'react';
import apiClient, { getAccessToken } from '../api/client';

const getSocketUrl = () => {
  const apiUrl = new URL(apiClient.defaults.baseURL || '/api', window.location.href);
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  apiUrl.pathname = '/ws/changes/';
  apiUrl.search = '';
  return apiUrl.toString();
};

export const useRealtimeChanges = ({ enabled, onChanges, onReconnect, onUnauthorized }) => {
  const handlers = useRef({ onChanges, onReconnect, onUnauthorized });
  useEffect(() => {
    handlers.current = { onChanges, onReconnect, onUnauthorized };
  }, [onChanges, onReconnect, onUnauthorized]);

  useEffect(() => {
    if (!enabled) return undefined;

    let stopped = false;
    let socket = null;
    let retryTimer = null;
    let flushTimer = null;
    let attempts = 0;
    let readyBefore = false;
    const pendingModules = new Set();
    const recentIds = new Set();

    const flush = () => {
      flushTimer = null;
      if (pendingModules.size === 0) return;
      const modules = [...pendingModules];
      pendingModules.clear();
      handlers.current.onChanges?.(modules);
    };

    const connect = () => {
      if (stopped || socket) return;
      socket = new WebSocket(getSocketUrl());
      socket.onopen = () => {
        socket.send(JSON.stringify({ type: 'auth', token: getAccessToken() }));
      };
      socket.onmessage = (message) => {
        let event;
        try { event = JSON.parse(message.data); } catch { return; }
        if (event.type === 'ready') {
          attempts = 0;
          if (readyBefore) handlers.current.onReconnect?.();
          readyBefore = true;
          return;
        }
        if (event.type !== 'change' || !Array.isArray(event.modules)) return;
        if (recentIds.has(event.event_id)) return;
        recentIds.add(event.event_id);
        if (recentIds.size > 100) recentIds.delete(recentIds.values().next().value);
        event.modules.forEach((module) => pendingModules.add(module));
        if (!flushTimer) flushTimer = window.setTimeout(flush, 150);
      };
      socket.onclose = async (event) => {
        socket = null;
        if (stopped) return;
        if (event.code === 4401) {
          try {
            await apiClient.get('/auth/me/');
          } catch (error) {
            if (error.response?.status === 401) {
              handlers.current.onUnauthorized?.();
              return;
            }
          }
        }
        if (stopped) return;
        attempts += 1;
        const delay = Math.min(1000 * (2 ** Math.min(attempts, 5)), 30000);
        retryTimer = window.setTimeout(connect, delay);
      };
    };

    const onOnline = () => {
      if (!socket && !retryTimer) connect();
    };
    window.addEventListener('online', onOnline);
    connect();

    return () => {
      stopped = true;
      window.removeEventListener('online', onOnline);
      window.clearTimeout(retryTimer);
      window.clearTimeout(flushTimer);
      socket?.close();
    };
  }, [enabled]);
};

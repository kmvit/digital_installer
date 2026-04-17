import { useState, useEffect, useCallback } from 'react';
import { syncPendingRequests, getPendingCount } from '../sync';

/**
 * Хук для отслеживания онлайн/офлайн статуса
 * и автосинхронизации при восстановлении сети.
 */
export default function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingCount, setPendingCount] = useState(0);
  const [syncing, setSyncing] = useState(false);

  const refreshPendingCount = useCallback(async () => {
    const count = await getPendingCount();
    setPendingCount(count);
  }, []);

  const doSync = useCallback(async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      const result = await syncPendingRequests();
      setPendingCount(result.remaining);
      return result;
    } finally {
      setSyncing(false);
    }
  }, [syncing]);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      // Автосинхронизация при восстановлении сети
      doSync();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Начальный подсчёт pending
    refreshPendingCount();

    // Периодическая проверка pending (каждые 30 сек)
    const interval = setInterval(refreshPendingCount, 30000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, [doSync, refreshPendingCount]);

  return { isOnline, pendingCount, syncing, doSync, refreshPendingCount };
}

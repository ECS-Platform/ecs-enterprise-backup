import { useState, useEffect, useCallback } from 'react';

export function useAutoRefresh(intervalMs = 60000) {
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refresh = useCallback(() => {
    setIsRefreshing(true);
    setTimeout(() => {
      setLastRefresh(new Date());
      setIsRefreshing(false);
    }, 800);
  }, []);

  useEffect(() => {
    const timer = setInterval(refresh, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, refresh]);

  return { lastRefresh, isRefreshing, refresh };
}

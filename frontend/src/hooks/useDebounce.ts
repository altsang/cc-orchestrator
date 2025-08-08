// Debounce hook for optimizing API calls

import { useCallback, useRef } from 'react';

export function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout>();

  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args);
      }, delay);
    },
    [callback, delay]
  ) as T;

  return debouncedCallback;
}

export function useDebouncedRefetchers(refetchers: Record<string, () => void>, delay = 1000) {
  const debouncedInstances = useDebounce(refetchers.instances, delay);
  const debouncedTasks = useDebounce(refetchers.tasks, delay);
  const debouncedHealth = useDebounce(refetchers.health, delay);
  const debouncedAlerts = useDebounce(refetchers.alerts, delay);

  return {
    instances: debouncedInstances,
    tasks: debouncedTasks,
    health: debouncedHealth,
    alerts: debouncedAlerts,
  };
}

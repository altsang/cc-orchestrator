// React hooks for API data management

import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import type {
  Instance,
  Task,
  Worktree,
  Alert,
  HealthCheck,
  Configuration,
  PaginatedResponse,
  APIResponse,
  InstanceFilter,
  TaskFilter,
  WorktreeFilter,
} from '../types';

// Generic API hook for data fetching
export function useApiData<T>(
  fetcher: () => Promise<T>,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetcher();
      setData(result);
    } catch (err) {
      console.error('API fetch error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, dependencies);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

// Instances hooks
export function useInstances(
  page: number = 1,
  size: number = 20,
  filters?: InstanceFilter
) {
  return useApiData(
    () => apiService.getInstances(page, size, filters),
    [page, size, filters]
  );
}

export function useInstance(id: number) {
  return useApiData(
    () => apiService.getInstance(id),
    [id]
  );
}

export function useInstanceOperations() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startInstance = useCallback(async (id: number): Promise<Instance | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.startInstance(id);
      return response.data || null;
    } catch (err) {
      console.error('Start instance error:', err);
      setError(err instanceof Error ? err.message : 'Failed to start instance');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const stopInstance = useCallback(async (id: number): Promise<Instance | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.stopInstance(id);
      return response.data || null;
    } catch (err) {
      console.error('Stop instance error:', err);
      setError(err instanceof Error ? err.message : 'Failed to stop instance');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const createInstance = useCallback(async (data: Partial<Instance>): Promise<Instance | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.createInstance(data);
      return response.data || null;
    } catch (err) {
      console.error('Create instance error:', err);
      setError(err instanceof Error ? err.message : 'Failed to create instance');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateInstance = useCallback(async (id: number, data: Partial<Instance>): Promise<Instance | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.updateInstance(id, data);
      return response.data || null;
    } catch (err) {
      console.error('Update instance error:', err);
      setError(err instanceof Error ? err.message : 'Failed to update instance');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteInstance = useCallback(async (id: number): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await apiService.deleteInstance(id);
      return true;
    } catch (err) {
      console.error('Delete instance error:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete instance');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    startInstance,
    stopInstance,
    createInstance,
    updateInstance,
    deleteInstance,
    loading,
    error,
  };
}

// Tasks hooks
export function useTasks(
  page: number = 1,
  size: number = 20,
  filters?: TaskFilter
) {
  return useApiData(
    () => apiService.getTasks(page, size, filters),
    [page, size, filters]
  );
}

export function useTask(id: number) {
  return useApiData(
    () => apiService.getTask(id),
    [id]
  );
}

export function useTaskOperations() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startTask = useCallback(async (id: number): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.startTask(id);
      return response.data || null;
    } catch (err) {
      console.error('Start task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to start task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const completeTask = useCallback(async (id: number, results?: Record<string, any>): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.completeTask(id, results);
      return response.data || null;
    } catch (err) {
      console.error('Complete task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to complete task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelTask = useCallback(async (id: number): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.cancelTask(id);
      return response.data || null;
    } catch (err) {
      console.error('Cancel task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to cancel task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const assignTask = useCallback(async (id: number, instanceId: number): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.assignTask(id, instanceId);
      return response.data || null;
    } catch (err) {
      console.error('Assign task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to assign task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const unassignTask = useCallback(async (id: number): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.unassignTask(id);
      return response.data || null;
    } catch (err) {
      console.error('Unassign task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to unassign task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const createTask = useCallback(async (data: Partial<Task>): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.createTask(data);
      return response.data || null;
    } catch (err) {
      console.error('Create task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to create task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateTask = useCallback(async (id: number, data: Partial<Task>): Promise<Task | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.updateTask(id, data);
      return response.data || null;
    } catch (err) {
      console.error('Update task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to update task');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteTask = useCallback(async (id: number): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      await apiService.deleteTask(id);
      return true;
    } catch (err) {
      console.error('Delete task error:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete task');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    startTask,
    completeTask,
    cancelTask,
    assignTask,
    unassignTask,
    createTask,
    updateTask,
    deleteTask,
    loading,
    error,
  };
}

// Worktrees hooks
export function useWorktrees(
  page: number = 1,
  size: number = 20,
  filters?: WorktreeFilter
) {
  return useApiData(
    () => apiService.getWorktrees(page, size, filters),
    [page, size, filters]
  );
}

export function useWorktree(id: number) {
  return useApiData(
    () => apiService.getWorktree(id),
    [id]
  );
}

// Health hooks
export function useHealthOverview() {
  return useApiData(
    () => apiService.getHealthOverview(),
    []
  );
}

export function useHealthChecks(
  page: number = 1,
  size: number = 20,
  instanceId?: number
) {
  return useApiData(
    () => apiService.getHealthChecks(page, size, instanceId),
    [page, size, instanceId]
  );
}

// Alerts hooks
export function useAlerts(
  page: number = 1,
  size: number = 20,
  level?: string,
  instanceId?: number
) {
  return useApiData(
    () => apiService.getAlerts(page, size, level, instanceId),
    [page, size, level, instanceId]
  );
}

export function useRecentCriticalAlerts(instanceId?: number) {
  return useApiData(
    () => apiService.getRecentCriticalAlerts(instanceId),
    [instanceId]
  );
}

// Configuration hooks
export function useConfigurations(
  page: number = 1,
  size: number = 20,
  scope?: string,
  instanceId?: number
) {
  return useApiData(
    () => apiService.getConfigurations(page, size, scope, instanceId),
    [page, size, scope, instanceId]
  );
}

// System status hook
export function useSystemStatus() {
  const [systemStatus, setSystemStatus] = useState({
    isConnected: false,
    serverInfo: null as any,
  });

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const [pingResult, systemInfo] = await Promise.all([
          apiService.ping(),
          apiService.getSystemInfo(),
        ]);

        setSystemStatus({
          isConnected: pingResult.status === 'ok',
          serverInfo: systemInfo,
        });
      } catch (error) {
        console.error('System status check failed:', error);
        setSystemStatus({
          isConnected: false,
          serverInfo: null,
        });
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return systemStatus;
}
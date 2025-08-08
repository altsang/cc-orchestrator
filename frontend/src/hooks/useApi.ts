// React hooks for API data management

import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { apiService } from '../services/api';
import logger from '../utils/logger';
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
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await fetcher();
      setData(result);
    } catch (err) {
      logger.error('API fetch error', err as Error);
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, dependencies);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startInstance = useCallback(async (id: number): Promise<Instance | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.startInstance(id);
      toast.success('Instance started successfully');
      return response;
    } catch (err) {
      logger.error('Start instance error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to start instance');
      toast.error('Failed to start instance');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const stopInstance = useCallback(async (id: number): Promise<Instance | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.stopInstance(id);
      toast.success('Instance stopped successfully');
      return response;
    } catch (err) {
      logger.error('Stop instance error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to stop instance');
      toast.error('Failed to stop instance');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createInstance = useCallback(async (data: Partial<Instance>): Promise<Instance | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.createInstance(data);
      toast.success('Instance created successfully');
      return response;
    } catch (err) {
      logger.error('Create instance error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to create instance');
      toast.error('Failed to create instance');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateInstance = useCallback(async (id: number, data: Partial<Instance>): Promise<Instance | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.updateInstance(id, data);
      toast.success('Instance updated successfully');
      return response;
    } catch (err) {
      logger.error('Update instance error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to update instance');
      toast.error('Failed to update instance');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteInstance = useCallback(async (id: number): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      await apiService.deleteInstance(id);
      toast.success('Instance deleted successfully');
      return true;
    } catch (err) {
      logger.error('Delete instance error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to delete instance');
      toast.error('Failed to delete instance');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    startInstance,
    stopInstance,
    createInstance,
    updateInstance,
    deleteInstance,
    isLoading,
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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startTask = useCallback(async (id: number): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.startTask(id);
      toast.success('Task started successfully');
      return response;
    } catch (err) {
      logger.error('Start task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to start task');
      toast.error('Failed to start task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const completeTask = useCallback(async (id: number, results?: Record<string, any>): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = results ? await apiService.completeTask(id, results) : await apiService.completeTask(id);
      toast.success('Task completed successfully');
      return response;
    } catch (err) {
      logger.error('Complete task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to complete task');
      toast.error('Failed to complete task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const cancelTask = useCallback(async (id: number): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.cancelTask(id);
      toast.success('Task cancelled successfully');
      return response;
    } catch (err) {
      logger.error('Cancel task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to cancel task');
      toast.error('Failed to cancel task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const assignTask = useCallback(async (id: number, instanceId: number): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.assignTask(id, instanceId);
      toast.success('Task assigned successfully');
      return response;
    } catch (err) {
      logger.error('Assign task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to assign task');
      toast.error('Failed to assign task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const unassignTask = useCallback(async (id: number): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.unassignTask(id);
      toast.success('Task unassigned successfully');
      return response;
    } catch (err) {
      logger.error('Unassign task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to unassign task');
      toast.error('Failed to unassign task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createTask = useCallback(async (data: Partial<Task>): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.createTask(data);
      toast.success('Task created successfully');
      return response;
    } catch (err) {
      logger.error('Create task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to create task');
      toast.error('Failed to create task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateTask = useCallback(async (id: number, data: Partial<Task>): Promise<Task | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiService.updateTask(id, data);
      toast.success('Task updated successfully');
      return response;
    } catch (err) {
      logger.error('Update task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to update task');
      toast.error('Failed to update task');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteTask = useCallback(async (id: number): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      await apiService.deleteTask(id);
      toast.success('Task deleted successfully');
      return true;
    } catch (err) {
      logger.error('Delete task error', err as Error);
      setError(err instanceof Error ? err.message : 'Failed to delete task');
      toast.error('Failed to delete task');
      throw err;
    } finally {
      setIsLoading(false);
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
    isLoading,
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
export function useHealth(
  page: number = 1,
  size: number = 20
) {
  return useApiData(
    () => apiService.getHealth(page, size),
    [page, size]
  );
}

export function useHealthOverview() {
  return useApiData(
    () => apiService.getHealth(1, 20),
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
    () => apiService.getAlerts(1, 5, {
      severity: 'critical',
      status: 'active',
    }),
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
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [instances, tasks, alerts] = await Promise.all([
        apiService.getInstances(1, 1000), // Get all instances
        apiService.getTasks(1, 1000), // Get all tasks
        apiService.getAlerts(1, 1000), // Get all alerts
      ]);

      // Aggregate statistics
      const instancesRunning = instances.items.filter(i => i.status === 'running').length;
      const instancesStopped = instances.items.filter(i => i.status === 'stopped').length;
      const instancesFailed = instances.items.filter(i => i.status === 'failed').length;

      const tasksActive = tasks.items.filter(t => t.status === 'running').length;
      const tasksCompleted = tasks.items.filter(t => t.status === 'completed').length;
      const tasksFailed = tasks.items.filter(t => t.status === 'failed').length;

      const alertsActive = alerts.items.filter(a => a.status === 'active').length;
      const alertsCritical = alerts.items.filter(a => a.severity === 'critical' && a.status === 'active').length;

      // Mock uptime calculation
      const uptimeHours = 72.5;

      const result = {
        instancesRunning,
        instancesStopped,
        instancesFailed,
        tasksActive,
        tasksCompleted,
        tasksFailed,
        alertsActive,
        alertsCritical,
        uptimeHours,
      };
      setData(result);
    } catch (err) {
      logger.error('System status check failed:', err as Error);
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}

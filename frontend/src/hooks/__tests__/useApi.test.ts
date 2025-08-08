import { renderHook, act } from '@testing-library/react';
import toast from 'react-hot-toast';
import { apiService } from '../../services/api';
import logger from '../../utils/logger';
import {
  useInstances,
  useTasks,
  useWorktrees,
  useHealth,
  useAlerts,
  useInstanceOperations,
  useTaskOperations,
  useSystemStatus,
  useHealthOverview,
  useRecentCriticalAlerts,
} from '../useApi';
import { InstanceStatus, TaskStatus, AlertSeverity } from '../../types';

// Mock dependencies
jest.mock('../../services/api');
jest.mock('react-hot-toast');
jest.mock('../../utils/logger');

const mockApiService = apiService as jest.Mocked<typeof apiService>;
const mockToast = toast as jest.Mocked<typeof toast>;
const mockLogger = logger as jest.Mocked<typeof logger>;

describe('useApi hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useInstances', () => {
    const mockInstances = {
      items: [
        {
          id: 1,
          instance_id: 'inst-1',
          issue_id: 'ISSUE-1',
          status: InstanceStatus.RUNNING,
          branch: 'main',
          workspace_path: '/workspace',
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T01:00:00Z',
          metadata: {},
        },
      ],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    };

    it('should fetch instances on mount', async () => {
      mockApiService.getInstances.mockResolvedValue(mockInstances);

      const { result } = renderHook(() => useInstances());

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeNull();
      expect(result.current.error).toBeNull();

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledWith(1, 20, undefined);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toEqual(mockInstances);
      expect(result.current.error).toBeNull();
    });

    it('should fetch instances with custom parameters', async () => {
      mockApiService.getInstances.mockResolvedValue(mockInstances);
      const filters = { status: InstanceStatus.RUNNING };

      const { result } = renderHook(() => useInstances(2, 10, filters));

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledWith(2, 10, filters);
    });

    it('should handle fetch errors', async () => {
      const error = new Error('Fetch failed');
      mockApiService.getInstances.mockRejectedValue(error);

      const { result } = renderHook(() => useInstances());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeNull();
      expect(result.current.error).toBe(error);
      expect(mockLogger.error).toHaveBeenCalledWith('API fetch error', error);
    });

    it('should refetch when refetch is called', async () => {
      mockApiService.getInstances.mockResolvedValue(mockInstances);

      const { result } = renderHook(() => useInstances());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledTimes(1);

      await act(async () => {
        result.current.refetch();
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledTimes(2);
    });

    it('should update parameters and refetch', async () => {
      mockApiService.getInstances.mockResolvedValue(mockInstances);

      const { result, rerender } = renderHook(
        ({ page, size, filters }) => useInstances(page, size, filters),
        { initialProps: { page: 1, size: 20, filters: undefined } }
      );

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledWith(1, 20, undefined);

      rerender({ page: 2, size: 10, filters: { status: InstanceStatus.RUNNING } });

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledWith(2, 10, { status: InstanceStatus.RUNNING });
    });
  });

  describe('useTasks', () => {
    const mockTasks = {
      items: [
        {
          id: 1,
          task_id: 'task-1',
          title: 'Test Task',
          description: 'Test description',
          status: TaskStatus.PENDING,
          priority: 'high',
          assigned_instance_id: null,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T01:00:00Z',
          metadata: {},
        },
      ],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    };

    it('should fetch tasks on mount', async () => {
      mockApiService.getTasks.mockResolvedValue(mockTasks);

      const { result } = renderHook(() => useTasks());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getTasks).toHaveBeenCalledWith(1, 20, undefined);
      expect(result.current.data).toEqual(mockTasks);
    });

    it('should handle task fetch errors', async () => {
      const error = new Error('Task fetch failed');
      mockApiService.getTasks.mockRejectedValue(error);

      const { result } = renderHook(() => useTasks());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.error).toBe(error);
      expect(mockLogger.error).toHaveBeenCalledWith('API fetch error', error);
    });
  });

  describe('useInstanceOperations', () => {
    it('should start instance successfully', async () => {
      const updatedInstance = {
        id: 1,
        instance_id: 'inst-1',
        issue_id: 'ISSUE-1',
        status: InstanceStatus.RUNNING,
        branch: 'main',
        workspace_path: '/workspace',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };
      mockApiService.startInstance.mockResolvedValue(updatedInstance);

      const { result } = renderHook(() => useInstanceOperations());

      expect(result.current.isLoading).toBe(false);

      await act(async () => {
        const response = await result.current.startInstance(1);
        expect(response).toEqual(updatedInstance);
      });

      expect(mockApiService.startInstance).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Instance started successfully');
      expect(result.current.isLoading).toBe(false);
    });

    it('should handle start instance errors', async () => {
      const error = new Error('Start failed');
      mockApiService.startInstance.mockRejectedValue(error);

      const { result } = renderHook(() => useInstanceOperations());

      await act(async () => {
        await expect(result.current.startInstance(1)).rejects.toBe(error);
      });

      expect(mockToast.error).toHaveBeenCalledWith('Failed to start instance');
      expect(mockLogger.error).toHaveBeenCalledWith('Start instance error', error);
    });

    it('should stop instance successfully', async () => {
      const updatedInstance = {
        id: 1,
        instance_id: 'inst-1',
        issue_id: 'ISSUE-1',
        status: InstanceStatus.STOPPED,
        branch: 'main',
        workspace_path: '/workspace',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };
      mockApiService.stopInstance.mockResolvedValue(updatedInstance);

      const { result } = renderHook(() => useInstanceOperations());

      await act(async () => {
        const response = await result.current.stopInstance(1);
        expect(response).toEqual(updatedInstance);
      });

      expect(mockApiService.stopInstance).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Instance stopped successfully');
    });

    it('should create instance successfully', async () => {
      const newInstance = {
        id: 2,
        instance_id: 'inst-2',
        issue_id: 'ISSUE-2',
        status: InstanceStatus.INITIALIZING,
        branch: 'feature',
        workspace_path: '/workspace',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };
      const createRequest = { issue_id: 'ISSUE-2', branch: 'feature' };
      mockApiService.createInstance.mockResolvedValue(newInstance);

      const { result } = renderHook(() => useInstanceOperations());

      await act(async () => {
        const response = await result.current.createInstance(createRequest);
        expect(response).toEqual(newInstance);
      });

      expect(mockApiService.createInstance).toHaveBeenCalledWith(createRequest);
      expect(mockToast.success).toHaveBeenCalledWith('Instance created successfully');
    });

    it('should update instance successfully', async () => {
      const updatedInstance = {
        id: 1,
        instance_id: 'inst-1',
        issue_id: 'ISSUE-1',
        status: InstanceStatus.RUNNING,
        branch: 'updated-branch',
        workspace_path: '/workspace',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T02:00:00Z',
        metadata: {},
      };
      const updateRequest = { branch: 'updated-branch' };
      mockApiService.updateInstance.mockResolvedValue(updatedInstance);

      const { result } = renderHook(() => useInstanceOperations());

      await act(async () => {
        const response = await result.current.updateInstance(1, updateRequest);
        expect(response).toEqual(updatedInstance);
      });

      expect(mockApiService.updateInstance).toHaveBeenCalledWith(1, updateRequest);
      expect(mockToast.success).toHaveBeenCalledWith('Instance updated successfully');
    });

    it('should delete instance successfully', async () => {
      mockApiService.deleteInstance.mockResolvedValue(undefined);

      const { result } = renderHook(() => useInstanceOperations());

      await act(async () => {
        await result.current.deleteInstance(1);
      });

      expect(mockApiService.deleteInstance).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Instance deleted successfully');
    });
  });

  describe('useTaskOperations', () => {
    it('should start task successfully', async () => {
      const updatedTask = {
        id: 1,
        task_id: 'task-1',
        title: 'Test Task',
        description: 'Test description',
        status: TaskStatus.RUNNING,
        priority: 'high',
        assigned_instance_id: 1,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };
      mockApiService.startTask.mockResolvedValue(updatedTask);

      const { result } = renderHook(() => useTaskOperations());

      await act(async () => {
        const response = await result.current.startTask(1);
        expect(response).toEqual(updatedTask);
      });

      expect(mockApiService.startTask).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Task started successfully');
    });

    it('should complete task successfully', async () => {
      const completedTask = {
        id: 1,
        task_id: 'task-1',
        title: 'Test Task',
        description: 'Test description',
        status: TaskStatus.COMPLETED,
        priority: 'high',
        assigned_instance_id: 1,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T02:00:00Z',
        metadata: {},
      };
      mockApiService.completeTask.mockResolvedValue(completedTask);

      const { result } = renderHook(() => useTaskOperations());

      await act(async () => {
        const response = await result.current.completeTask(1);
        expect(response).toEqual(completedTask);
      });

      expect(mockApiService.completeTask).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Task completed successfully');
    });

    it('should cancel task successfully', async () => {
      const cancelledTask = {
        id: 1,
        task_id: 'task-1',
        title: 'Test Task',
        description: 'Test description',
        status: TaskStatus.CANCELLED,
        priority: 'high',
        assigned_instance_id: null,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T02:00:00Z',
        metadata: {},
      };
      mockApiService.cancelTask.mockResolvedValue(cancelledTask);

      const { result } = renderHook(() => useTaskOperations());

      await act(async () => {
        const response = await result.current.cancelTask(1);
        expect(response).toEqual(cancelledTask);
      });

      expect(mockApiService.cancelTask).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Task cancelled successfully');
    });

    it('should assign task to instance successfully', async () => {
      const assignedTask = {
        id: 1,
        task_id: 'task-1',
        title: 'Test Task',
        description: 'Test description',
        status: TaskStatus.PENDING,
        priority: 'high',
        assigned_instance_id: 1,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };
      mockApiService.assignTask.mockResolvedValue(assignedTask);

      const { result } = renderHook(() => useTaskOperations());

      await act(async () => {
        const response = await result.current.assignTask(1, 1);
        expect(response).toEqual(assignedTask);
      });

      expect(mockApiService.assignTask).toHaveBeenCalledWith(1, 1);
      expect(mockToast.success).toHaveBeenCalledWith('Task assigned successfully');
    });

    it('should unassign task successfully', async () => {
      const unassignedTask = {
        id: 1,
        task_id: 'task-1',
        title: 'Test Task',
        description: 'Test description',
        status: TaskStatus.PENDING,
        priority: 'high',
        assigned_instance_id: null,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T01:00:00Z',
        metadata: {},
      };
      mockApiService.unassignTask.mockResolvedValue(unassignedTask);

      const { result } = renderHook(() => useTaskOperations());

      await act(async () => {
        const response = await result.current.unassignTask(1);
        expect(response).toEqual(unassignedTask);
      });

      expect(mockApiService.unassignTask).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Task unassigned successfully');
    });
  });

  describe('useSystemStatus', () => {
    it('should fetch system status', async () => {
      const systemStatus = {
        instancesRunning: 5,
        instancesStopped: 2,
        instancesFailed: 1,
        tasksActive: 10,
        tasksCompleted: 50,
        tasksFailed: 3,
        alertsActive: 2,
        alertsCritical: 0,
        uptimeHours: 72.5,
      };

      mockApiService.getInstances.mockResolvedValue({
        items: Array(8).fill(null).map((_, i) => ({
          id: i,
          status: i < 5 ? InstanceStatus.RUNNING : i < 7 ? InstanceStatus.STOPPED : InstanceStatus.FAILED,
        })),
        total: 8,
        page: 1,
        size: 20,
        pages: 1,
      });

      mockApiService.getTasks.mockResolvedValue({
        items: Array(63).fill(null).map((_, i) => ({
          id: i,
          status: i < 10 ? TaskStatus.RUNNING : i < 60 ? TaskStatus.COMPLETED : TaskStatus.FAILED,
        })),
        total: 63,
        page: 1,
        size: 20,
        pages: 4,
      });

      mockApiService.getAlerts.mockResolvedValue({
        items: Array(2).fill(null).map((_, i) => ({
          id: i,
          severity: AlertSeverity.MEDIUM,
          status: 'active',
        })),
        total: 2,
        page: 1,
        size: 20,
        pages: 1,
      });

      const { result } = renderHook(() => useSystemStatus());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.data).toMatchObject({
        instancesRunning: 5,
        instancesStopped: 2,
        instancesFailed: 1,
        tasksActive: 10,
        tasksCompleted: 50,
        tasksFailed: 3,
        alertsActive: 2,
        alertsCritical: 0,
      });
    });

    it('should handle system status fetch errors', async () => {
      const error = new Error('System status fetch failed');
      mockApiService.getInstances.mockRejectedValue(error);

      const { result } = renderHook(() => useSystemStatus());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.error).toBe(error);
      expect(mockLogger.error).toHaveBeenCalledWith('System status check failed:', error);
    });
  });

  describe('useHealthOverview', () => {
    it('should fetch health overview', async () => {
      const healthData = {
        items: [
          {
            id: 1,
            component: 'database',
            status: 'healthy',
            message: 'All systems operational',
            checked_at: '2023-01-01T00:00:00Z',
            metadata: {},
          },
          {
            id: 2,
            component: 'api',
            status: 'degraded',
            message: 'High response times',
            checked_at: '2023-01-01T00:00:00Z',
            metadata: {},
          },
        ],
        total: 2,
        page: 1,
        size: 20,
        pages: 1,
      };

      mockApiService.getHealth.mockResolvedValue(healthData);

      const { result } = renderHook(() => useHealthOverview());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.data).toEqual(healthData);
      expect(mockApiService.getHealth).toHaveBeenCalledWith(1, 20);
    });
  });

  describe('useRecentCriticalAlerts', () => {
    it('should fetch recent critical alerts', async () => {
      const alertsData = {
        items: [
          {
            id: 1,
            alert_id: 'alert-1',
            title: 'Critical Error',
            message: 'System failure detected',
            severity: AlertSeverity.CRITICAL,
            status: 'active',
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z',
            metadata: {},
          },
        ],
        total: 1,
        page: 1,
        size: 5,
        pages: 1,
      };

      mockApiService.getAlerts.mockResolvedValue(alertsData);

      const { result } = renderHook(() => useRecentCriticalAlerts());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.data).toEqual(alertsData);
      expect(mockApiService.getAlerts).toHaveBeenCalledWith(1, 5, {
        severity: AlertSeverity.CRITICAL,
        status: 'active',
      });
    });
  });

  describe('error handling and edge cases', () => {
    it('should handle network timeouts', async () => {
      const timeoutError = { code: 'ECONNABORTED', message: 'timeout' };
      mockApiService.getInstances.mockRejectedValue(timeoutError);

      const { result } = renderHook(() => useInstances());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.error).toBe(timeoutError);
      expect(mockLogger.error).toHaveBeenCalledWith('API fetch error', timeoutError);
    });

    it('should handle server errors', async () => {
      const serverError = { response: { status: 500 }, message: 'Internal Server Error' };
      mockApiService.getInstances.mockRejectedValue(serverError);

      const { result } = renderHook(() => useInstances());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.error).toBe(serverError);
    });

    it('should handle concurrent operations', async () => {
      mockApiService.startInstance.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({} as any), 100))
      );

      const { result } = renderHook(() => useInstanceOperations());

      // Start multiple concurrent operations
      const promises = [
        result.current.startInstance(1),
        result.current.startInstance(2),
        result.current.startInstance(3),
      ];

      await act(async () => {
        await Promise.all(promises);
      });

      expect(mockApiService.startInstance).toHaveBeenCalledTimes(3);
    });

    it('should handle empty responses', async () => {
      mockApiService.getInstances.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        size: 20,
        pages: 0,
      });

      const { result } = renderHook(() => useInstances());

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.data?.items).toEqual([]);
      expect(result.current.data?.total).toBe(0);
    });

    it('should handle pagination edge cases', async () => {
      mockApiService.getInstances.mockResolvedValue({
        items: [],
        total: 1000,
        page: 999,
        size: 1,
        pages: 1000,
      });

      const { result } = renderHook(() => useInstances(999, 1));

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(mockApiService.getInstances).toHaveBeenCalledWith(999, 1, undefined);
      expect(result.current.data?.page).toBe(999);
    });
  });
});
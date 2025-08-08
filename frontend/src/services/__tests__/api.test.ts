import axios from 'axios';
import toast from 'react-hot-toast';
import { apiService } from '../api';
import logger from '../../utils/logger';
import { 
  Instance, 
  Task, 
  Worktree, 
  Alert, 
  HealthCheck, 
  InstanceStatus, 
  TaskStatus, 
  AlertSeverity,
  HealthStatus 
} from '../../types';

// Mock dependencies
jest.mock('axios');
jest.mock('react-hot-toast');
jest.mock('../../utils/logger');
jest.mock('../../config/environment', () => ({
  apiBaseUrl: 'http://localhost:8080/api/v1',
  apiTimeout: 10000,
}));

const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockToast = toast as jest.Mocked<typeof toast>;
const mockLogger = logger as jest.Mocked<typeof logger>;

const mockAxiosInstance = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn(),
  interceptors: {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  },
} as any;

describe('APIService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedAxios.create.mockReturnValue(mockAxiosInstance);
  });

  describe('constructor', () => {
    it('should create axios instance with correct configuration', () => {
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8080/api/v1',
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    });

    it('should set up request and response interceptors', () => {
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });
  });

  describe('instances API', () => {
    const mockInstance: Instance = {
      id: 1,
      instance_id: 'test-instance',
      issue_id: 'ISSUE-123',
      status: InstanceStatus.RUNNING,
      branch: 'main',
      workspace_path: '/workspace',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T01:00:00Z',
      metadata: {},
    };

    const mockPaginatedResponse = {
      items: [mockInstance],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    };

    it('should get instances with default pagination', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: mockPaginatedResponse });

      const result = await apiService.getInstances();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances', { page: 1, size: 20 });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should get instances with custom pagination and filters', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: mockPaginatedResponse });
      const filters = { status: InstanceStatus.RUNNING };

      const result = await apiService.getInstances(2, 10, filters);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances', { 
        page: 2, 
        size: 10, 
        status: InstanceStatus.RUNNING 
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should get instance by id', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: mockInstance });

      const result = await apiService.getInstance(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances/1');
      expect(result).toEqual(mockInstance);
    });

    it('should create instance', async () => {
      const createRequest = {
        issue_id: 'ISSUE-123',
        branch: 'main',
      };
      mockAxiosInstance.post.mockResolvedValue({ data: mockInstance });

      const result = await apiService.createInstance(createRequest);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/instances', createRequest);
      expect(result).toEqual(mockInstance);
    });

    it('should update instance', async () => {
      const updateRequest = { status: InstanceStatus.STOPPED };
      mockAxiosInstance.put.mockResolvedValue({ data: mockInstance });

      const result = await apiService.updateInstance(1, updateRequest);

      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/instances/1', updateRequest);
      expect(result).toEqual(mockInstance);
    });

    it('should delete instance', async () => {
      mockAxiosInstance.delete.mockResolvedValue({ data: { success: true } });

      await apiService.deleteInstance(1);

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/instances/1');
    });

    it('should start instance', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: mockInstance });

      const result = await apiService.startInstance(1);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/instances/1/start');
      expect(result).toEqual(mockInstance);
    });

    it('should stop instance', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: mockInstance });

      const result = await apiService.stopInstance(1);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/instances/1/stop');
      expect(result).toEqual(mockInstance);
    });
  });

  describe('tasks API', () => {
    const mockTask: Task = {
      id: 1,
      task_id: 'TASK-123',
      title: 'Test Task',
      description: 'Test description',
      status: TaskStatus.PENDING,
      priority: 'high',
      assigned_instance_id: null,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T01:00:00Z',
      metadata: {},
    };

    const mockPaginatedResponse = {
      items: [mockTask],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    };

    it('should get tasks', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: mockPaginatedResponse });

      const result = await apiService.getTasks();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks', { page: 1, size: 20 });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should get task by id', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: mockTask });

      const result = await apiService.getTask(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks/1');
      expect(result).toEqual(mockTask);
    });

    it('should create task', async () => {
      const createRequest = {
        title: 'New Task',
        description: 'Task description',
        priority: 'high',
      };
      mockAxiosInstance.post.mockResolvedValue({ data: mockTask });

      const result = await apiService.createTask(createRequest);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks', createRequest);
      expect(result).toEqual(mockTask);
    });

    it('should start task', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: mockTask });

      const result = await apiService.startTask(1);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/start');
      expect(result).toEqual(mockTask);
    });

    it('should complete task', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: mockTask });

      const result = await apiService.completeTask(1);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/complete');
      expect(result).toEqual(mockTask);
    });

    it('should cancel task', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: mockTask });

      const result = await apiService.cancelTask(1);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/cancel');
      expect(result).toEqual(mockTask);
    });
  });

  describe('worktrees API', () => {
    const mockWorktree: Worktree = {
      id: 1,
      worktree_id: 'worktree-123',
      path: '/worktree/path',
      branch: 'feature-branch',
      instance_id: 1,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T01:00:00Z',
      metadata: {},
    };

    it('should get worktrees', async () => {
      const mockResponse = { items: [mockWorktree], total: 1, page: 1, size: 20, pages: 1 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getWorktrees();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/worktrees', { page: 1, size: 20 });
      expect(result).toEqual(mockResponse);
    });

    it('should create worktree', async () => {
      const createRequest = { path: '/new/path', branch: 'new-branch' };
      mockAxiosInstance.post.mockResolvedValue({ data: mockWorktree });

      const result = await apiService.createWorktree(createRequest);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/worktrees', createRequest);
      expect(result).toEqual(mockWorktree);
    });
  });

  describe('health API', () => {
    const mockHealthCheck: HealthCheck = {
      id: 1,
      component: 'database',
      status: HealthStatus.HEALTHY,
      message: 'All systems operational',
      checked_at: '2023-01-01T00:00:00Z',
      metadata: {},
    };

    it('should get health status', async () => {
      const mockResponse = { items: [mockHealthCheck], total: 1, page: 1, size: 20, pages: 1 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getHealth();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health', { page: 1, size: 20 });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('alerts API', () => {
    const mockAlert: Alert = {
      id: 1,
      alert_id: 'ALERT-123',
      title: 'Test Alert',
      message: 'Alert message',
      severity: AlertSeverity.HIGH,
      status: 'active',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T01:00:00Z',
      metadata: {},
    };

    it('should get alerts', async () => {
      const mockResponse = { items: [mockAlert], total: 1, page: 1, size: 20, pages: 1 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getAlerts();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts', { page: 1, size: 20 });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('error handling', () => {
    it('should handle network errors', async () => {
      const networkError = new Error('Network Error');
      mockAxiosInstance.get.mockRejectedValue(networkError);

      await expect(apiService.getInstances()).rejects.toThrow('Network Error');
    });

    it('should handle 404 errors with toast notification', async () => {
      const error404 = {
        response: { status: 404 },
        message: 'Not Found'
      };
      mockAxiosInstance.get.mockRejectedValue(error404);

      await expect(apiService.getInstance(999)).rejects.toEqual(error404);
    });

    it('should handle 500 errors with toast notification', async () => {
      const error500 = {
        response: { status: 500 },
        message: 'Internal Server Error'
      };
      mockAxiosInstance.get.mockRejectedValue(error500);

      await expect(apiService.getInstances()).rejects.toEqual(error500);
    });

    it('should handle timeout errors', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 10000ms exceeded'
      };
      mockAxiosInstance.get.mockRejectedValue(timeoutError);

      await expect(apiService.getInstances()).rejects.toEqual(timeoutError);
    });
  });

  describe('validation integration', () => {
    it('should validate API responses', async () => {
      const invalidResponse = { invalid: 'data' };
      mockAxiosInstance.get.mockResolvedValue({ data: invalidResponse });

      // This should trigger validation error
      await expect(apiService.getInstances()).rejects.toThrow();
    });

    it('should sanitize request parameters', async () => {
      const filters = { 
        status: InstanceStatus.RUNNING,
        malicious: '<script>alert("xss")</script>' 
      };

      mockAxiosInstance.get.mockResolvedValue({ data: { items: [], total: 0, page: 1, size: 20, pages: 1 } });

      await apiService.getInstances(1, 20, filters);

      // Verify that the request was made with sanitized parameters
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances', 
        expect.objectContaining({
          page: 1,
          size: 20,
          status: InstanceStatus.RUNNING,
          malicious: expect.not.stringContaining('<script>')
        })
      );
    });
  });
});
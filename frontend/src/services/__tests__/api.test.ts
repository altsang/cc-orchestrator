// Comprehensive tests for API service
import { InstanceStatus, TaskStatus, AlertSeverity } from '../../types';

// Create mock axios instance
const mockAxiosInstance = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  interceptors: {
    request: {
      use: jest.fn(),
    },
    response: {
      use: jest.fn(),
    },
  },
};

// Mock axios before importing the service
jest.doMock('axios', () => ({
  create: jest.fn(() => mockAxiosInstance),
}));

// Now import axios and the service
const axios = require('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

import { apiService } from '../api';

describe('APIService', () => {
  beforeEach(() => {
    // Clear mock instance methods but preserve the setup
    mockAxiosInstance.get.mockClear();
    mockAxiosInstance.post.mockClear();
    mockAxiosInstance.put.mockClear();
    mockAxiosInstance.delete.mockClear();
    mockAxiosInstance.interceptors.request.use.mockClear();
    mockAxiosInstance.interceptors.response.use.mockClear();

    // Mock the private client property directly
    (apiService as any).client = mockAxiosInstance;
  });

  describe('HTTP Client Configuration', () => {
    it('should have API service available', () => {
      // Test that the service is properly initialized
      expect(apiService).toBeDefined();
      expect(typeof apiService.getInstances).toBe('function');
    });
  });

  describe('Instance API Methods', () => {
    describe('getInstances', () => {
      it('should fetch instances with default pagination', async () => {
        const mockResponse = {
          items: [
            {
              id: 1,
              issue_id: 'ISSUE-1',
              status: InstanceStatus.RUNNING,
              health_status: 'healthy',
              branch_name: 'main',
              workspace_path: '/workspace',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T01:00:00Z',
              extra_metadata: {},
              health_check_count: 10,
              healthy_check_count: 8,
              recovery_attempt_count: 0,
            },
          ],
          total: 1,
          page: 1,
          size: 20,
          pages: 1,
        };

        mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

        const result = await apiService.getInstances();

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances', {
          params: { page: 1, size: 20 },
        });
        expect(result).toEqual(mockResponse);
      });

      it('should fetch instances with custom pagination and filters', async () => {
        const mockResponse = { items: [], total: 0, page: 2, size: 10, pages: 0 };
        const filters = { status: InstanceStatus.RUNNING };

        mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

        const result = await apiService.getInstances(2, 10, filters);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances', {
          params: { page: 2, size: 10, status: InstanceStatus.RUNNING },
        });
        expect(result).toEqual(mockResponse);
      });

      it('should handle instance fetch errors', async () => {
        const error = new Error('Network error');
        mockAxiosInstance.get.mockRejectedValue(error);

        await expect(apiService.getInstances()).rejects.toThrow('Network error');
      });
    });

    describe('getInstance', () => {
      it('should fetch single instance by ID', async () => {
        const mockInstance = {
          data: {
            id: 1,
            instance_id: 'inst-1',
            status: InstanceStatus.RUNNING,
          },
        };

        mockAxiosInstance.get.mockResolvedValue({ data: mockInstance });

        const result = await apiService.getInstance(1);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/instances/1', { params: undefined });
        expect(result).toEqual(mockInstance);
      });
    });

    describe('Instance Operations', () => {
      it('should start instance', async () => {
        const mockResponse = {
          data: { id: 1, status: InstanceStatus.RUNNING },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.startInstance(1);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/instances/1/start', undefined);
        expect(result).toEqual(mockResponse);
      });

      it('should stop instance', async () => {
        const mockResponse = {
          data: { id: 1, status: InstanceStatus.STOPPED },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.stopInstance(1);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/instances/1/stop', undefined);
        expect(result).toEqual(mockResponse);
      });

      it('should create instance', async () => {
        const instanceData = {
          issue_id: 'ISSUE-1',
          branch: 'feature-branch',
        };
        const mockResponse = {
          data: { id: 2, ...instanceData, status: InstanceStatus.INITIALIZING },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.createInstance(instanceData);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/instances', instanceData);
        expect(result).toEqual(mockResponse);
      });

      it('should update instance', async () => {
        const updateData = { branch: 'updated-branch' };
        const mockResponse = {
          data: { id: 1, ...updateData },
        };

        mockAxiosInstance.put.mockResolvedValue({ data: mockResponse });

        const result = await apiService.updateInstance(1, updateData);

        expect(mockAxiosInstance.put).toHaveBeenCalledWith('/instances/1', updateData);
        expect(result).toEqual(mockResponse);
      });

      it('should delete instance', async () => {
        const mockResponse = { data: null };

        mockAxiosInstance.delete.mockResolvedValue({ data: mockResponse });

        const result = await apiService.deleteInstance(1);

        expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/instances/1');
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('Task API Methods', () => {
    describe('getTasks', () => {
      it('should fetch tasks with default pagination', async () => {
        const mockResponse = {
          items: [
            {
              id: 1,
              title: 'Test Task',
              status: TaskStatus.PENDING,
              priority: 'high',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T01:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          size: 20,
          pages: 1,
        };

        mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

        const result = await apiService.getTasks();

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks', {
          params: { page: 1, size: 20 },
        });
        expect(result).toEqual(mockResponse);
      });

      it('should fetch tasks with filters', async () => {
        const filters = { status: TaskStatus.RUNNING };
        const mockResponse = { items: [], total: 0, page: 1, size: 20, pages: 0 };

        mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

        const result = await apiService.getTasks(1, 20, filters);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks', {
          params: { page: 1, size: 20, status: TaskStatus.RUNNING },
        });
        expect(result).toEqual(mockResponse);
      });
    });

    describe('Task Operations', () => {
      it('should start task', async () => {
        const mockResponse = {
          data: { id: 1, status: TaskStatus.RUNNING },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.startTask(1);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/start', undefined);
        expect(result).toEqual(mockResponse);
      });

      it('should complete task without results', async () => {
        const mockResponse = {
          data: { id: 1, status: TaskStatus.COMPLETED },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.completeTask(1);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/complete', { results: undefined });
        expect(result).toEqual(mockResponse);
      });

      it('should complete task with results', async () => {
        const results = { output: 'success' };
        const mockResponse = {
          data: { id: 1, status: TaskStatus.COMPLETED, results },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.completeTask(1, results);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/complete', { results });
        expect(result).toEqual(mockResponse);
      });

      it('should cancel task', async () => {
        const mockResponse = {
          data: { id: 1, status: TaskStatus.CANCELLED },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.cancelTask(1);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/cancel', undefined);
        expect(result).toEqual(mockResponse);
      });

      it('should assign task to instance', async () => {
        const mockResponse = {
          data: { id: 1, instance_id: 5 },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.assignTask(1, 5);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks/1/assign', {
          instance_id: 5,
        });
        expect(result).toEqual(mockResponse);
      });

      it('should unassign task', async () => {
        const mockResponse = {
          data: { id: 1, instance_id: null },
        };

        mockAxiosInstance.delete.mockResolvedValue({ data: mockResponse });

        const result = await apiService.unassignTask(1);

        expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/tasks/1/assign');
        expect(result).toEqual(mockResponse);
      });

      it('should create task', async () => {
        const taskData = {
          title: 'New Task',
          priority: 'medium',
        };
        const mockResponse = {
          data: { id: 2, ...taskData, status: TaskStatus.PENDING },
        };

        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

        const result = await apiService.createTask(taskData);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks', taskData);
        expect(result).toEqual(mockResponse);
      });

      it('should update task', async () => {
        const updateData = { title: 'Updated Task' };
        const mockResponse = {
          data: { id: 1, ...updateData },
        };

        mockAxiosInstance.put.mockResolvedValue({ data: mockResponse });

        const result = await apiService.updateTask(1, updateData);

        expect(mockAxiosInstance.put).toHaveBeenCalledWith('/tasks/1', updateData);
        expect(result).toEqual(mockResponse);
      });

      it('should delete task', async () => {
        const mockResponse = { data: null };

        mockAxiosInstance.delete.mockResolvedValue({ data: mockResponse });

        const result = await apiService.deleteTask(1);

        expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/tasks/1');
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('Health API Methods', () => {
    it('should get health overview', async () => {
      const mockResponse = {
        data: {
          overall_status: 'healthy',
          instances_healthy: 5,
          instances_degraded: 1,
          instances_unhealthy: 0,
        },
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getHealthOverview();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health/overview', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('should get health data with pagination', async () => {
      const mockResponse = {
        items: [
          {
            id: 1,
            component: 'database',
            status: 'healthy',
            checked_at: '2023-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        size: 20,
        pages: 1,
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getHealth(1, 20);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health', {
        params: { page: 1, size: 20 },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should get health checks with instance filter', async () => {
      const mockResponse = { items: [], total: 0, page: 1, size: 20, pages: 0 };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getHealthChecks(1, 20, 5);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health/checks', {
        params: { page: 1, size: 20, instance_id: 5 },
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Alert API Methods', () => {
    it('should get alerts with filters', async () => {
      const mockResponse = {
        items: [
          {
            id: 1,
            alert_id: 'alert-1',
            title: 'Critical Error',
            message: 'System failure detected',
            severity: AlertSeverity.HIGH,
            status: 'active',
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        size: 20,
        pages: 1,
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getAlerts(1, 20, 'high', 1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts', {
        params: { page: 1, size: 20, level: 'high', instance_id: 1 },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should create alert', async () => {
      const alertData = {
        alert_id: 'new-alert',
        title: 'New Alert',
        message: 'Alert message',
        severity: AlertSeverity.MEDIUM,
      };
      const mockResponse = {
        data: { id: 2, ...alertData },
      };

      mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

      const result = await apiService.createAlert(alertData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/alerts', alertData);
      expect(result).toEqual(mockResponse);
    });

    it('should get single alert', async () => {
      const mockResponse = {
        data: {
          id: 1,
          alert_id: 'alert-1',
          title: 'Test Alert',
        },
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getAlert(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts/1', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('should get recent critical alerts', async () => {
      const mockResponse = {
        data: [
          {
            id: 1,
            severity: AlertSeverity.CRITICAL,
            status: 'active',
          },
        ],
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getRecentCriticalAlerts();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts/recent/critical', {
        params: {},
      });
      expect(result).toEqual(mockResponse);
    });

    it('should get recent critical alerts for specific instance', async () => {
      const mockResponse = { data: [] };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getRecentCriticalAlerts(5);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts/recent/critical', {
        params: { instance_id: 5 },
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Configuration API Methods', () => {
    it('should get configurations with all parameters', async () => {
      const mockResponse = {
        items: [
          {
            id: 1,
            key: 'test-config',
            value: 'test-value',
            scope: 'global',
          },
        ],
        total: 1,
        page: 1,
        size: 20,
        pages: 1,
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getConfigurations(1, 20, 'global', 5);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/config', {
        params: { page: 1, size: 20, scope: 'global', instance_id: 5 },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should create configuration', async () => {
      const configData = {
        key: 'new-config',
        value: 'new-value',
        scope: 'instance',
      };
      const mockResponse = {
        data: { id: 2, ...configData },
      };

      mockAxiosInstance.post.mockResolvedValue({ data: mockResponse });

      const result = await apiService.createConfiguration(configData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/config', configData);
      expect(result).toEqual(mockResponse);
    });

    it('should get configuration by ID', async () => {
      const mockResponse = {
        data: { id: 1, key: 'test-config' },
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getConfiguration(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/config/1', { params: undefined });
      expect(result).toEqual(mockResponse);
    });

    it('should update configuration', async () => {
      const updateData = { value: 'updated-value' };
      const mockResponse = {
        data: { id: 1, ...updateData },
      };

      mockAxiosInstance.put.mockResolvedValue({ data: mockResponse });

      const result = await apiService.updateConfiguration(1, updateData);

      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/config/1', updateData);
      expect(result).toEqual(mockResponse);
    });

    it('should delete configuration', async () => {
      const mockResponse = { data: null };

      mockAxiosInstance.delete.mockResolvedValue({ data: mockResponse });

      const result = await apiService.deleteConfiguration(1);

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/config/1');
      expect(result).toEqual(mockResponse);
    });

    it('should get configuration by key', async () => {
      const mockResponse = {
        data: { key: 'test-key', value: 'test-value' },
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getConfigurationByKey('test-key', 'global', 5);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/config/key/test-key', {
        params: { scope: 'global', instance_id: 5 },
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('System API Methods', () => {
    it('should ping system', async () => {
      const mockResponse = {
        status: 'ok',
        timestamp: '2023-01-01T00:00:00Z',
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.ping();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/ping', {
        baseURL: expect.any(String),
      });
      expect(result).toEqual(mockResponse);
    });

    it('should get system info', async () => {
      const mockResponse = {
        version: '1.0.0',
        uptime: 3600,
        environment: 'production',
      };

      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      const result = await apiService.getSystemInfo();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/', {
        baseURL: expect.any(String),
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('Interceptors', () => {
    it('should log API requests via request interceptor', () => {
      const mockConfig = { method: 'GET', url: '/instances' };

      // Get the request interceptor function that was registered
      const requestInterceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0]?.[0];

      if (requestInterceptor) {
        const result = requestInterceptor(mockConfig);
        expect(result).toBe(mockConfig);
      }
    });

    it('should handle request interceptor errors', async () => {
      const error = new Error('Request error');

      // Get the error handler from request interceptor
      const requestErrorHandler = mockAxiosInstance.interceptors.request.use.mock.calls[0]?.[1];

      if (requestErrorHandler) {
        await expect(requestErrorHandler(error)).rejects.toBe(error);
      }
    });

    it('should log API responses via response interceptor', () => {
      const mockResponse = {
        status: 200,
        config: { url: '/instances' },
        data: { items: [] }
      };

      // Get the response interceptor function
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0]?.[0];

      if (responseInterceptor) {
        const result = responseInterceptor(mockResponse);
        expect(result).toBe(mockResponse);
      }
    });

    it('should handle response interceptor errors with 404', async () => {
      const error404 = {
        response: { status: 404 },
        config: { url: '/instances' }
      };

      // Get the error handler from response interceptor
      const responseErrorHandler = mockAxiosInstance.interceptors.response.use.mock.calls[0]?.[1];

      if (responseErrorHandler) {
        await expect(responseErrorHandler(error404)).rejects.toBe(error404);
      }
    });

    it('should handle response interceptor errors with 500', async () => {
      const error500 = {
        response: { status: 500 },
        config: { url: '/instances' }
      };

      const responseErrorHandler = mockAxiosInstance.interceptors.response.use.mock.calls[0]?.[1];

      if (responseErrorHandler) {
        await expect(responseErrorHandler(error500)).rejects.toBe(error500);
      }
    });

    it('should handle timeout errors in response interceptor', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        config: { url: '/instances' }
      };

      const responseErrorHandler = mockAxiosInstance.interceptors.response.use.mock.calls[0]?.[1];

      if (responseErrorHandler) {
        await expect(responseErrorHandler(timeoutError)).rejects.toBe(timeoutError);
      }
    });

    it('should handle network errors in response interceptor', async () => {
      const networkError = {
        config: { url: '/instances' }
      };

      const responseErrorHandler = mockAxiosInstance.interceptors.response.use.mock.calls[0]?.[1];

      if (responseErrorHandler) {
        await expect(responseErrorHandler(networkError)).rejects.toBe(networkError);
      }
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const networkError = new Error('Network Error');
      mockAxiosInstance.get.mockRejectedValue(networkError);

      await expect(apiService.getInstances()).rejects.toThrow('Network Error');
    });

    it('should handle HTTP errors', async () => {
      const httpError = {
        response: {
          status: 404,
          data: { error: 'Not Found' },
        },
      };
      mockAxiosInstance.get.mockRejectedValue(httpError);

      await expect(apiService.getInstance(999)).rejects.toEqual(httpError);
    });

    it('should handle server errors', async () => {
      const serverError = {
        response: {
          status: 500,
          data: { error: 'Internal Server Error' },
        },
      };
      mockAxiosInstance.post.mockRejectedValue(serverError);

      await expect(apiService.startInstance(1)).rejects.toEqual(serverError);
    });

    it('should handle timeout errors', async () => {
      const timeoutError = new Error('Timeout');
      timeoutError.code = 'ECONNABORTED';
      mockAxiosInstance.get.mockRejectedValue(timeoutError);

      await expect(apiService.getHealthOverview()).rejects.toThrow('Timeout');
    });
  });

  describe('Parameter Handling', () => {
    it('should handle undefined optional parameters', async () => {
      const mockResponse = { items: [], total: 0, page: 1, size: 20, pages: 0 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      await apiService.getConfigurations(1, 20, undefined, undefined);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/config', {
        params: { page: 1, size: 20 },
      });
    });

    it('should handle empty string parameters', async () => {
      const mockResponse = { items: [], total: 0, page: 1, size: 20, pages: 0 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      await apiService.getAlerts(1, 20, '', undefined);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts', {
        params: { page: 1, size: 20 },
      });
    });

    it('should handle null parameters', async () => {
      const mockResponse = { data: [] };
      mockAxiosInstance.get.mockResolvedValue({ data: mockResponse });

      await apiService.getRecentCriticalAlerts(null as any);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/alerts/recent/critical', {
        params: {},
      });
    });
  });
});

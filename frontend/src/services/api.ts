// API service for CC-Orchestrator backend communication

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import toast from 'react-hot-toast';
import { apiBaseUrl, apiTimeout } from '../config/environment';
import { validateApiResponse, sanitizeObject, paginatedResponseSchema, instanceSchema, taskSchema } from '../validation/schemas';
import logger from '../utils/logger';
import type {
  APIResponse,
  PaginatedResponse,
  Instance,
  Task,
  Worktree,
  Alert,
  HealthCheck,
  Configuration,
  InstanceFilter,
  TaskFilter,
  WorktreeFilter,
  LogEntry,
  LogSearchRequest,
  LogSearchResponse,
  LogExportRequest,
  LogStreamFilter,
  LogStreamStats,
} from '../types';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: apiBaseUrl,
      timeout: apiTimeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for logging and auth
    this.client.interceptors.request.use(
      (config) => {
        logger.apiRequest(config.method || 'GET', config.url || '');
        return config;
      },
      (error) => {
        logger.apiError('Request interceptor error', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        logger.apiResponse(response.status, response.config.url || '');
        return response;
      },
      (error) => {
        logger.apiError('Response interceptor error', error, error.config?.url);

        // Show user-friendly error messages
        if (error.response?.status === 404) {
          toast.error('Resource not found');
        } else if (error.response?.status === 500) {
          toast.error('Server error occurred');
        } else if (error.code === 'ECONNABORTED') {
          toast.error('Request timeout - please try again');
        } else if (!error.response) {
          toast.error('Network error - please check your connection');
        }

        return Promise.reject(error);
      }
    );
  }

  // Generic request methods
  private async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(url, { params });
    return response.data;
  }

  private async post<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(url, data);
    return response.data;
  }

  private async put<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(url, data);
    return response.data;
  }

  private async delete<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url);
    return response.data;
  }

  // Instance API methods
  async getInstances(
    page: number = 1,
    size: number = 20,
    filters?: InstanceFilter
  ): Promise<PaginatedResponse<Instance>> {
    const params = sanitizeObject({ page, size, ...filters });
    const response = await this.get<PaginatedResponse<Instance>>('/instances', params);

    // Validate response structure
    const paginatedData = validateApiResponse(response, paginatedResponseSchema);

    // Validate each instance in the items array
    const validatedInstances = paginatedData.items.map(item =>
      validateApiResponse(item, instanceSchema)
    );

    return {
      ...paginatedData,
      items: validatedInstances,
    };
  }

  async getInstance(id: number): Promise<APIResponse<Instance>> {
    return this.get<APIResponse<Instance>>(`/instances/${id}`);
  }

  async createInstance(data: Partial<Instance>): Promise<APIResponse<Instance>> {
    return this.post<APIResponse<Instance>>('/instances', data);
  }

  async updateInstance(id: number, data: Partial<Instance>): Promise<APIResponse<Instance>> {
    return this.put<APIResponse<Instance>>(`/instances/${id}`, data);
  }

  async deleteInstance(id: number): Promise<APIResponse<null>> {
    return this.delete<APIResponse<null>>(`/instances/${id}`);
  }

  async startInstance(id: number): Promise<APIResponse<Instance>> {
    return this.post<APIResponse<Instance>>(`/instances/${id}/start`);
  }

  async stopInstance(id: number): Promise<APIResponse<Instance>> {
    return this.post<APIResponse<Instance>>(`/instances/${id}/stop`);
  }

  async getInstanceStatus(id: number): Promise<APIResponse<any>> {
    return this.get<APIResponse<any>>(`/instances/${id}/status`);
  }

  async getInstanceTasks(
    id: number,
    page: number = 1,
    size: number = 20
  ): Promise<PaginatedResponse<Task>> {
    return this.get<PaginatedResponse<Task>>(`/instances/${id}/tasks`, { page, size });
  }

  // Task API methods
  async getTasks(
    page: number = 1,
    size: number = 20,
    filters?: TaskFilter
  ): Promise<PaginatedResponse<Task>> {
    const params = { page, size, ...filters };
    return this.get<PaginatedResponse<Task>>('/tasks', params);
  }

  async getTask(id: number): Promise<APIResponse<Task>> {
    return this.get<APIResponse<Task>>(`/tasks/${id}`);
  }

  async createTask(data: Partial<Task>): Promise<APIResponse<Task>> {
    return this.post<APIResponse<Task>>('/tasks', data);
  }

  async updateTask(id: number, data: Partial<Task>): Promise<APIResponse<Task>> {
    return this.put<APIResponse<Task>>(`/tasks/${id}`, data);
  }

  async deleteTask(id: number): Promise<APIResponse<null>> {
    return this.delete<APIResponse<null>>(`/tasks/${id}`);
  }

  async startTask(id: number): Promise<APIResponse<Task>> {
    return this.post<APIResponse<Task>>(`/tasks/${id}/start`);
  }

  async completeTask(id: number, results?: Record<string, any>): Promise<APIResponse<Task>> {
    return this.post<APIResponse<Task>>(`/tasks/${id}/complete`, { results });
  }

  async cancelTask(id: number): Promise<APIResponse<Task>> {
    return this.post<APIResponse<Task>>(`/tasks/${id}/cancel`);
  }

  async assignTask(id: number, instanceId: number): Promise<APIResponse<Task>> {
    return this.post<APIResponse<Task>>(`/tasks/${id}/assign`, { instance_id: instanceId });
  }

  async unassignTask(id: number): Promise<APIResponse<Task>> {
    return this.delete<APIResponse<Task>>(`/tasks/${id}/assign`);
  }

  // Worktree API methods
  async getWorktrees(
    page: number = 1,
    size: number = 20,
    filters?: WorktreeFilter
  ): Promise<PaginatedResponse<Worktree>> {
    const params = { page, size, ...filters };
    return this.get<PaginatedResponse<Worktree>>('/worktrees', params);
  }

  async getWorktree(id: number): Promise<APIResponse<Worktree>> {
    return this.get<APIResponse<Worktree>>(`/worktrees/${id}`);
  }

  async createWorktree(data: Partial<Worktree>): Promise<APIResponse<Worktree>> {
    return this.post<APIResponse<Worktree>>('/worktrees', data);
  }

  async updateWorktree(id: number, data: Partial<Worktree>): Promise<APIResponse<Worktree>> {
    return this.put<APIResponse<Worktree>>(`/worktrees/${id}`, data);
  }

  async deleteWorktree(id: number): Promise<APIResponse<null>> {
    return this.delete<APIResponse<null>>(`/worktrees/${id}`);
  }

  // Health API methods
  async getHealth(
    page: number = 1,
    size: number = 20
  ): Promise<PaginatedResponse<HealthCheck>> {
    const params = { page, size };
    return this.get<PaginatedResponse<HealthCheck>>('/health', params);
  }

  async getHealthChecks(
    page: number = 1,
    size: number = 20,
    instanceId?: number
  ): Promise<PaginatedResponse<HealthCheck>> {
    const params = { page, size };
    if (instanceId) {
      (params as any).instance_id = instanceId;
    }
    return this.get<PaginatedResponse<HealthCheck>>('/health/checks', params);
  }

  async getHealthOverview(): Promise<APIResponse<any>> {
    return this.get<APIResponse<any>>('/health/overview');
  }

  // Alert API methods
  async getAlerts(
    page: number = 1,
    size: number = 20,
    level?: string,
    instanceId?: number
  ): Promise<PaginatedResponse<Alert>> {
    const params = { page, size };
    if (level) (params as any).level = level;
    if (instanceId) (params as any).instance_id = instanceId;
    return this.get<PaginatedResponse<Alert>>('/alerts', params);
  }

  async createAlert(data: Partial<Alert>): Promise<APIResponse<Alert>> {
    return this.post<APIResponse<Alert>>('/alerts', data);
  }

  async getAlert(id: number): Promise<APIResponse<Alert>> {
    return this.get<APIResponse<Alert>>(`/alerts/${id}`);
  }

  async getRecentCriticalAlerts(instanceId?: number): Promise<APIResponse<Alert[]>> {
    const params = instanceId ? { instance_id: instanceId } : {};
    return this.get<APIResponse<Alert[]>>('/alerts/recent/critical', params);
  }

  // Configuration API methods
  async getConfigurations(
    page: number = 1,
    size: number = 20,
    scope?: string,
    instanceId?: number
  ): Promise<PaginatedResponse<Configuration>> {
    const params = { page, size };
    if (scope) (params as any).scope = scope;
    if (instanceId) (params as any).instance_id = instanceId;
    return this.get<PaginatedResponse<Configuration>>('/config', params);
  }

  async createConfiguration(data: Partial<Configuration>): Promise<APIResponse<Configuration>> {
    return this.post<APIResponse<Configuration>>('/config', data);
  }

  async getConfiguration(id: number): Promise<APIResponse<Configuration>> {
    return this.get<APIResponse<Configuration>>(`/config/${id}`);
  }

  async updateConfiguration(id: number, data: Partial<Configuration>): Promise<APIResponse<Configuration>> {
    return this.put<APIResponse<Configuration>>(`/config/${id}`, data);
  }

  async deleteConfiguration(id: number): Promise<APIResponse<null>> {
    return this.delete<APIResponse<null>>(`/config/${id}`);
  }

  async getConfigurationByKey(key: string, scope?: string, instanceId?: number): Promise<APIResponse<Configuration>> {
    const params = { scope, instance_id: instanceId };
    return this.get<APIResponse<Configuration>>(`/config/key/${key}`, params);
  }

  // Log streaming API methods
  async searchLogs(searchRequest: LogSearchRequest): Promise<LogSearchResponse> {
    const params = sanitizeObject({
      query: searchRequest.query,
      level: searchRequest.level,
      context: searchRequest.context,
      instance_id: searchRequest.instance_id,
      task_id: searchRequest.task_id,
      start_time: searchRequest.start_time,
      end_time: searchRequest.end_time,
      regex_enabled: searchRequest.regex_enabled,
      case_sensitive: searchRequest.case_sensitive,
      limit: searchRequest.limit,
      offset: searchRequest.offset,
    });

    return this.get<LogSearchResponse>('/logs/search', params);
  }

  async exportLogs(exportRequest: LogExportRequest): Promise<void> {
    try {
      const response = await this.client.post('/logs/export', exportRequest, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Extract filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `logs_export.${exportRequest.format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      logger.info('Log export completed', { filename, format: exportRequest.format });
      toast.success('Logs exported successfully');
    } catch (error) {
      logger.error('Log export failed', error as Error);
      toast.error('Failed to export logs');
      throw error;
    }
  }

  async getLogLevels(): Promise<string[]> {
    return this.get<string[]>('/logs/levels');
  }

  async getLogContexts(): Promise<string[]> {
    return this.get<string[]>('/logs/contexts');
  }

  async getLogStats(): Promise<LogStreamStats> {
    return this.get<LogStreamStats>('/logs/stats');
  }

  async startLogStream(streamFilter: LogStreamFilter): Promise<{ stream_id: string; status: string }> {
    return this.post<{ stream_id: string; status: string }>('/logs/stream/start', streamFilter);
  }

  async stopLogStream(streamId: string): Promise<{ stream_id: string; status: string }> {
    return this.post<{ stream_id: string; status: string }>(`/logs/stream/${streamId}/stop`);
  }

  async cleanupLogs(olderThanHours: number = 24): Promise<{ deleted_count: number; remaining_count: number }> {
    const params = { older_than_hours: olderThanHours };
    return this.delete<{ deleted_count: number; remaining_count: number }>('/logs/cleanup', params);
  }

  // Utility methods
  async ping(): Promise<{ status: string }> {
    const response = await this.client.get('/ping', {
      baseURL: apiBaseUrl.replace('/api/v1', ''), // Use root endpoint for ping
    });
    return response.data;
  }

  async getSystemInfo(): Promise<any> {
    const response = await this.client.get('/', {
      baseURL: apiBaseUrl.replace('/api/v1', ''), // Use root endpoint for system info
    });
    return response.data;
  }
}

// Export singleton instance
export const apiService = new APIService();

// Convenient function exports for log operations
export const searchLogs = (searchRequest: LogSearchRequest) => apiService.searchLogs(searchRequest);
export const exportLogs = (exportRequest: LogExportRequest) => apiService.exportLogs(exportRequest);
export const getLogLevels = () => apiService.getLogLevels();
export const getLogContexts = () => apiService.getLogContexts();
export const getLogStats = () => apiService.getLogStats();
export const startLogStream = (streamFilter: LogStreamFilter) => apiService.startLogStream(streamFilter);
export const stopLogStream = (streamId: string) => apiService.stopLogStream(streamId);
export const cleanupLogs = (olderThanHours?: number) => apiService.cleanupLogs(olderThanHours);

export default apiService;

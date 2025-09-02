import { Instance, InstanceHealth, InstanceStatus } from '../types'
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

const API_BASE_URL = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1'

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: apiBaseUrl || API_BASE_URL,
      timeout: apiTimeout || 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for authentication
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('authToken');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  private async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    try {
      const response = await this.client.get<T>(endpoint, { params });
      return response.data;
    } catch (error) {
      logger.error('API GET request failed', error as Error);
      throw error;
    }
  }

  private async post<T>(endpoint: string, data?: any): Promise<T> {
    try {
      const response = await this.client.post<T>(endpoint, data);
      return response.data;
    } catch (error) {
      logger.error('API POST request failed', error as Error);
      throw error;
    }
  }

  private async put<T>(endpoint: string, data?: any): Promise<T> {
    try {
      const response = await this.client.put<T>(endpoint, data);
      return response.data;
    } catch (error) {
      logger.error('API PUT request failed', error as Error);
      throw error;
    }
  }

  private async delete<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    try {
      const response = await this.client.delete<T>(endpoint, { params });
      return response.data;
    } catch (error) {
      logger.error('API DELETE request failed', error as Error);
      throw error;
    }
  }

  // Instance endpoints
  async getInstances(statusFilter?: InstanceStatus): Promise<PaginatedResponse<Instance>> {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    return this.get<PaginatedResponse<Instance>>('/instances', params);
  }

  async getInstance(id: number): Promise<APIResponse<Instance>> {
    return this.get<APIResponse<Instance>>(`/instances/${id}`);
  }

  async createInstance(data: { issue_id: string; status: InstanceStatus }): Promise<APIResponse<Instance>> {
    return this.post<APIResponse<Instance>>('/instances', data);
  }

  async updateInstanceStatus(id: number, status: InstanceStatus): Promise<APIResponse<Instance>> {
    return this.put<APIResponse<Instance>>(`/instances/${id}/status`, { status });
  }

  // Instance control endpoints
  async startInstance(id: number): Promise<APIResponse<{ message: string; instance_id: string }>> {
    return this.post<APIResponse<{ message: string; instance_id: string }>>(`/instances/${id}/start`);
  }

  async stopInstance(id: number): Promise<APIResponse<{ message: string; instance_id: string }>> {
    return this.post<APIResponse<{ message: string; instance_id: string }>>(`/instances/${id}/stop`);
  }

  async restartInstance(id: number): Promise<APIResponse<{ message: string; instance_id: string }>> {
    return this.post<APIResponse<{ message: string; instance_id: string }>>(`/instances/${id}/restart`);
  }

  // Health and monitoring endpoints
  async getInstanceHealth(id: number): Promise<APIResponse<InstanceHealth>> {
    return this.get<APIResponse<InstanceHealth>>(`/instances/${id}/health`);
  }

  async getInstanceLogs(id: number, options?: { limit?: number; search?: string }): Promise<APIResponse<{
    instance_id: number;
    logs: any[];
    total: number;
    limit: number;
    search?: string;
  }>> {
    const params: Record<string, any> = {};
    if (options?.limit) params.limit = options.limit;
    if (options?.search) params.search = options.search;
    return this.get<APIResponse<{
      instance_id: number;
      logs: any[];
      total: number;
      limit: number;
      search?: string;
    }>>(`/instances/${id}/logs`, params);
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

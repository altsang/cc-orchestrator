import { Instance, InstanceHealth, InstanceStatus } from '../types'

const API_BASE_URL = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1'

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`)
    }

    return response.json()
  }

  // Instance endpoints
  async getInstances(statusFilter?: InstanceStatus): Promise<{ instances: Instance[]; total: number }> {
    const params = statusFilter ? new URLSearchParams({ status_filter: statusFilter }) : ''
    return this.request(`/instances${params ? '?' + params : ''}`)
  }

  async getInstance(id: number): Promise<Instance> {
    return this.request(`/instances/${id}`)
  }

  async createInstance(data: { issue_id: string; status: InstanceStatus }): Promise<Instance> {
    return this.request('/instances', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateInstanceStatus(id: number, status: InstanceStatus): Promise<Instance> {
    return this.request(`/instances/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  }

  // Instance control endpoints
  async startInstance(id: number): Promise<{ message: string; instance_id: string }> {
    return this.request(`/instances/${id}/start`, {
      method: 'POST',
    })
  }

  async stopInstance(id: number): Promise<{ message: string; instance_id: string }> {
    return this.request(`/instances/${id}/stop`, {
      method: 'POST',
    })
  }

  async restartInstance(id: number): Promise<{ message: string; instance_id: string }> {
    return this.request(`/instances/${id}/restart`, {
      method: 'POST',
    })
  }

  // Health and monitoring endpoints
  async getInstanceHealth(id: number): Promise<InstanceHealth> {
    return this.request(`/instances/${id}/health`)
  }

  async getInstanceLogs(id: number, options?: { limit?: number; search?: string }): Promise<{
    instance_id: number;
    logs: any[];
    total: number;
    limit: number;
    search?: string;
  }> {
    const params = new URLSearchParams()
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.search) params.append('search', options.search)

    return this.request(`/instances/${id}/logs${params.toString() ? '?' + params : ''}`)
  }
}

export const apiClient = new ApiClient()

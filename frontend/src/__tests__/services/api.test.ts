/**
 * @jest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import apiClient from '../../services/api'
import { InstanceStatus } from '../../types'

// Mock fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockClear()
  })

  describe('Authentication', () => {
    it('includes Authorization header when token is available', async () => {
      // Mock localStorage to return a token
      const mockToken = 'test-jwt-token'
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => mockToken),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
        key: vi.fn(),
        length: 0
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ instances: [], total: 0 })
      })

      await apiClient.getInstances()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`
          })
        })
      )
    })

    it('works without token when none available', async () => {
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
        key: vi.fn(),
        length: 0
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ instances: [], total: 0 })
      })

      await apiClient.getInstances()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            'Authorization': expect.any(String)
          })
        })
      )
    })
  })

  describe('Instance Operations', () => {
    beforeEach(() => {
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => 'test-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
        key: vi.fn(),
        length: 0
      })
    })

    it('gets instances successfully', async () => {
      const mockResponse = {
        instances: [
          {
            id: 1,
            issue_id: '123',
            status: InstanceStatus.RUNNING,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
            config: {}
          }
        ],
        total: 1
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await apiClient.getInstances()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances',
        expect.objectContaining({
          method: 'GET'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('gets single instance by ID', async () => {
      const mockInstance = {
        id: 1,
        issue_id: '123',
        status: InstanceStatus.RUNNING,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        config: {}
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockInstance
      })

      const result = await apiClient.getInstance(1)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1',
        expect.objectContaining({
          method: 'GET'
        })
      )
      expect(result).toEqual(mockInstance)
    })

    it('creates new instance', async () => {
      const newInstance = {
        issue_id: '456'
      }

      const mockResponse = {
        id: 2,
        issue_id: '456',
        status: InstanceStatus.INITIALIZING,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        config: {}
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await apiClient.createInstance(newInstance)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify(newInstance)
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('starts instance', async () => {
      const mockResponse = {
        message: 'Instance start requested',
        instance_id: '1'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await apiClient.startInstance(1)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1/start',
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('stops instance', async () => {
      const mockResponse = {
        message: 'Instance stop requested',
        instance_id: '1'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await apiClient.stopInstance(1)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1/stop',
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('restarts instance', async () => {
      const mockResponse = {
        message: 'Instance restart requested',
        instance_id: '1'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await apiClient.restartInstance(1)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1/restart',
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('gets instance health', async () => {
      const mockHealth = {
        instance_id: 1,
        status: InstanceStatus.RUNNING,
        health: 'healthy',
        cpu_usage: 25.5,
        memory_usage: 60.2,
        uptime_seconds: 3600
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealth
      })

      const result = await apiClient.getInstanceHealth(1)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1/health',
        expect.objectContaining({
          method: 'GET'
        })
      )
      expect(result).toEqual(mockHealth)
    })

    it('gets instance logs', async () => {
      const mockLogs = {
        instance_id: 1,
        logs: [
          { timestamp: '2024-01-01T00:00:00Z', level: 'INFO', message: 'Test log' }
        ],
        total: 1
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockLogs
      })

      const result = await apiClient.getInstanceLogs(1, { limit: 100 })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1/logs?limit=100',
        expect.objectContaining({
          method: 'GET'
        })
      )
      expect(result).toEqual(mockLogs)
    })
  })

  describe('Error Handling', () => {
    beforeEach(() => {
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => 'test-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
        key: vi.fn(),
        length: 0
      })
    })

    it('throws error for non-ok responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Instance not found' })
      })

      await expect(apiClient.getInstance(999)).rejects.toThrow()
    })

    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(apiClient.getInstances()).rejects.toThrow('Network error')
    })

    it('handles JSON parsing errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new Error('Invalid JSON') }
      })

      await expect(apiClient.getInstances()).rejects.toThrow()
    })

    it('handles 401 unauthorized responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'Token expired' })
      })

      await expect(apiClient.getInstances()).rejects.toThrow()
    })

    it('handles 429 rate limit responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: async () => ({ error: 'Rate limit exceeded' })
      })

      await expect(apiClient.getInstances()).rejects.toThrow()
    })
  })

  describe('Query Parameters', () => {
    beforeEach(() => {
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(() => 'test-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
        key: vi.fn(),
        length: 0
      })
    })

    it('handles query parameters correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ instances: [], total: 0 })
      })

      await apiClient.getInstances({ status: InstanceStatus.RUNNING })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances?status=RUNNING',
        expect.any(Object)
      )
    })

    it('handles multiple query parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ logs: [], total: 0 })
      })

      await apiClient.getInstanceLogs(1, { limit: 50, search: 'error' })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances/1/logs?limit=50&search=error',
        expect.any(Object)
      )
    })

    it('handles empty query parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ instances: [], total: 0 })
      })

      await apiClient.getInstances({})

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/instances',
        expect.any(Object)
      )
    })
  })
})
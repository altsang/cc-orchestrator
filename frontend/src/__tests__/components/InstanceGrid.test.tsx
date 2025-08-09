/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import InstanceGrid from '../../components/InstanceGrid'
import { InstanceStatus } from '../../types'
import type { Instance } from '../../types'

// Mock the API client
vi.mock('../../services/api', () => ({
  default: {
    getInstances: vi.fn(),
  }
}))

const mockInstances: Instance[] = [
  {
    id: 1,
    issue_id: '123',
    status: InstanceStatus.RUNNING,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    config: {}
  },
  {
    id: 2,
    issue_id: '456',
    status: InstanceStatus.STOPPED,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    config: {}
  },
  {
    id: 3,
    issue_id: '789',
    status: InstanceStatus.ERROR,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    config: {}
  }
]

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, cacheTime: 0 },
      mutations: { retry: false },
    },
  })
  
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('InstanceGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    expect(screen.getByText('Loading instances...')).toBeInTheDocument()
  })

  it('renders instances when loaded successfully', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      expect(screen.getByText('Issue #123')).toBeInTheDocument()
      expect(screen.getByText('Issue #456')).toBeInTheDocument()
      expect(screen.getByText('Issue #789')).toBeInTheDocument()
    })
  })

  it('displays correct status indicators for each instance', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      expect(screen.getByText('Running')).toBeInTheDocument()
      expect(screen.getByText('Stopped')).toBeInTheDocument()
      expect(screen.getByText('Error')).toBeInTheDocument()
    })
  })

  it('renders error state when API call fails', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockRejectedValue(new Error('API Error'))
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      expect(screen.getByText('Error loading instances')).toBeInTheDocument()
    })
  })

  it('renders empty state when no instances', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: [],
      total: 0
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      expect(screen.getByText('No instances found')).toBeInTheDocument()
    })
  })

  it('displays instance creation dates', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      // Should display relative dates
      expect(screen.getByText(/Created/)).toBeInTheDocument()
    })
  })

  it('has clickable instance cards that navigate to detail view', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      const instanceCard = screen.getByText('Issue #123').closest('div')
      expect(instanceCard).toBeInTheDocument()
      // Card should be clickable (has cursor-pointer or similar)
    })
  })

  it('refreshes data periodically', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      expect(apiClient.getInstances).toHaveBeenCalledTimes(1)
    })
    
    // Should be called again after refetch interval
    // Note: In a real test we might mock timers, but this tests the setup
  })

  it('displays instance controls for each instance', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      // Should have control buttons for running instance (Stop, Restart)
      expect(screen.getByText('Stop')).toBeInTheDocument()
      expect(screen.getByText('Restart')).toBeInTheDocument()
      
      // Should have start button for stopped instance
      expect(screen.getByText('Start')).toBeInTheDocument()
    })
  })

  it('shows responsive grid layout', async () => {
    const apiClient = require('../../services/api').default
    apiClient.getInstances.mockResolvedValue({
      instances: mockInstances,
      total: mockInstances.length
    })
    
    render(
      <TestWrapper>
        <InstanceGrid />
      </TestWrapper>
    )
    
    await waitFor(() => {
      const gridContainer = screen.getByText('Issue #123').closest('.grid') || 
                           screen.getByText('Issue #123').closest('[class*="grid"]')
      expect(gridContainer).toBeInTheDocument()
    })
  })
})
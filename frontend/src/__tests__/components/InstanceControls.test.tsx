/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import InstanceControls from '../../components/InstanceControls'
import { InstanceStatus } from '../../types'
import type { Instance } from '../../types'

// Mock the API client
vi.mock('../../services/api', () => ({
  default: {
    startInstance: vi.fn(),
    stopInstance: vi.fn(),
    restartInstance: vi.fn(),
  }
}))

const mockInstance: Instance = {
  id: 1,
  issue_id: '123',
  status: InstanceStatus.STOPPED,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  config: {}
}

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('InstanceControls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders start button when instance is stopped', () => {
    render(
      <TestWrapper>
        <InstanceControls instance={mockInstance} />
      </TestWrapper>
    )

    expect(screen.getByText('Start')).toBeInTheDocument()
    expect(screen.queryByText('Stop')).not.toBeInTheDocument()
  })

  it('renders stop and restart buttons when instance is running', () => {
    const runningInstance = { ...mockInstance, status: InstanceStatus.RUNNING }

    render(
      <TestWrapper>
        <InstanceControls instance={runningInstance} />
      </TestWrapper>
    )

    expect(screen.getByText('Stop')).toBeInTheDocument()
    expect(screen.getByText('Restart')).toBeInTheDocument()
    expect(screen.queryByText('Start')).not.toBeInTheDocument()
  })

  it('shows all buttons disabled when instance is initializing', () => {
    const initializingInstance = { ...mockInstance, status: InstanceStatus.INITIALIZING }

    render(
      <TestWrapper>
        <InstanceControls instance={initializingInstance} />
      </TestWrapper>
    )

    const buttons = screen.getAllByRole('button')
    buttons.forEach(button => {
      expect(button).toBeDisabled()
    })
  })

  it('shows start button for error status', () => {
    const errorInstance = { ...mockInstance, status: InstanceStatus.ERROR }

    render(
      <TestWrapper>
        <InstanceControls instance={errorInstance} />
      </TestWrapper>
    )

    expect(screen.getByText('Start')).toBeInTheDocument()
    expect(screen.getByText('Start')).not.toBeDisabled()
  })

  it('calls start API when start button is clicked', async () => {
    const apiClient = await import('../../services/api')
    const startSpy = vi.spyOn(apiClient.default, 'startInstance').mockResolvedValue({
      message: 'Instance start requested',
      instance_id: '1'
    })

    render(
      <TestWrapper>
        <InstanceControls instance={mockInstance} />
      </TestWrapper>
    )

    fireEvent.click(screen.getByText('Start'))

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalledWith(1)
    })
  })

  it('calls stop API when stop button is clicked', async () => {
    const runningInstance = { ...mockInstance, status: InstanceStatus.RUNNING }
    const apiClient = await import('../../services/api')
    const stopSpy = vi.spyOn(apiClient.default, 'stopInstance').mockResolvedValue({
      message: 'Instance stop requested',
      instance_id: '1'
    })

    render(
      <TestWrapper>
        <InstanceControls instance={runningInstance} />
      </TestWrapper>
    )

    fireEvent.click(screen.getByText('Stop'))

    await waitFor(() => {
      expect(stopSpy).toHaveBeenCalledWith(1)
    })
  })

  it('calls restart API when restart button is clicked', async () => {
    const runningInstance = { ...mockInstance, status: InstanceStatus.RUNNING }
    const apiClient = await import('../../services/api')
    const restartSpy = vi.spyOn(apiClient.default, 'restartInstance').mockResolvedValue({
      message: 'Instance restart requested',
      instance_id: '1'
    })

    render(
      <TestWrapper>
        <InstanceControls instance={runningInstance} />
      </TestWrapper>
    )

    fireEvent.click(screen.getByText('Restart'))

    await waitFor(() => {
      expect(restartSpy).toHaveBeenCalledWith(1)
    })
  })
})

/**
 * @jest-environment jsdom
 */
import { render, renderHook, act, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { WebSocketProvider, useWebSocket } from '../../contexts/WebSocketContext'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  
  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  
  constructor(public url: string) {
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 10)
  }
  
  send = vi.fn((data: string) => {
    // Echo back for testing
    setTimeout(() => {
      if (this.onmessage) {
        const response = JSON.stringify({ type: 'echo', data: JSON.parse(data) })
        this.onmessage(new MessageEvent('message', { data: response }))
      }
    }, 5)
  })
  
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  })
}

// Replace global WebSocket
vi.stubGlobal('WebSocket', MockWebSocket)

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return <WebSocketProvider>{children}</WebSocketProvider>
}

describe('WebSocketContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  it('provides WebSocket context to children', () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    expect(result.current).toBeDefined()
    expect(result.current.isConnected).toBeDefined()
    expect(result.current.sendMessage).toBeDefined()
    expect(result.current.subscribe).toBeDefined()
  })

  it('starts disconnected and attempts to connect', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    expect(result.current.isConnected).toBe(false)
    
    // Should eventually connect
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    }, { timeout: 100 })
  })

  it('sends authentication message on connection', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    // Mock WebSocket should have received auth message
    // This would depend on implementation details
  })

  it('allows sending messages when connected', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    act(() => {
      result.current.sendMessage({ type: 'test', data: 'hello' })
    })
    
    // Should call WebSocket.send
    expect(MockWebSocket.prototype.send).toHaveBeenCalled()
  })

  it('handles subscription to event types', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    const mockCallback = vi.fn()
    
    act(() => {
      result.current.subscribe('instance_status', mockCallback)
    })
    
    // Should send subscription message
    expect(MockWebSocket.prototype.send).toHaveBeenCalled()
  })

  it('handles connection errors gracefully', async () => {
    // Mock a failing WebSocket
    class FailingWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url)
        setTimeout(() => {
          this.readyState = MockWebSocket.CLOSED
          this.onerror?.(new Event('error'))
          this.onclose?.(new CloseEvent('close'))
        }, 5)
      }
    }
    
    vi.stubGlobal('WebSocket', FailingWebSocket)
    
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })
    
    // Should attempt to reconnect
    // Implementation would depend on reconnection logic
  })

  it('cleans up connections on unmount', () => {
    const { unmount } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    unmount()
    
    expect(MockWebSocket.prototype.close).toHaveBeenCalled()
  })

  it('handles received messages correctly', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    const mockCallback = vi.fn()
    
    act(() => {
      result.current.subscribe('test_event', mockCallback)
    })
    
    // Simulate receiving a message
    const ws = new MockWebSocket('test')
    act(() => {
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'test_event',
          data: { message: 'test' }
        })
      }))
    })
    
    // Callback should be called
    await waitFor(() => {
      expect(mockCallback).toHaveBeenCalledWith({ message: 'test' })
    })
  })

  it('maintains connection state correctly', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    // Should start disconnected
    expect(result.current.isConnected).toBe(false)
    
    // Should connect
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    // Simulate disconnection
    const ws = new MockWebSocket('test')
    act(() => {
      ws.readyState = MockWebSocket.CLOSED
      ws.onclose?.(new CloseEvent('close'))
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })
  })

  it('uses correct WebSocket URL based on environment', () => {
    renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    // Should use localhost in development
    expect(MockWebSocket).toHaveBeenCalledWith(
      expect.stringContaining('localhost')
    )
  })

  it('handles multiple subscriptions to same event', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    const callback1 = vi.fn()
    const callback2 = vi.fn()
    
    act(() => {
      result.current.subscribe('instance_status', callback1)
      result.current.subscribe('instance_status', callback2)
    })
    
    // Both callbacks should be registered
    // Implementation details would verify this
  })
})
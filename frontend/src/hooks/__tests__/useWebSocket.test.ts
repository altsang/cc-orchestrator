import { renderHook, act } from '@testing-library/react';
import { websocketService } from '../../services/websocket';
import logger from '../../utils/logger';
import { useDashboardWebSocket, useWebSocketConnection } from '../useWebSocket';
import { WebSocketMessage } from '../../types';

// Mock dependencies
jest.mock('../../services/websocket');
jest.mock('../../utils/logger');

const mockWebsocketService = websocketService as jest.Mocked<typeof websocketService>;
const mockLogger = logger as jest.Mocked<typeof logger>;

describe('useWebSocket hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useWebSocketConnection', () => {
    it('should initialize with disconnected state', () => {
      mockWebsocketService.isConnected.mockReturnValue(false);

      const { result } = renderHook(() => useWebSocketConnection());

      expect(result.current.isConnected).toBe(false);
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should connect to WebSocket on mount', async () => {
      mockWebsocketService.isConnected.mockReturnValue(false);
      mockWebsocketService.connect.mockResolvedValue(undefined);
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      expect(result.current.isConnecting).toBe(true);

      await act(async () => {
        // Simulate successful connection
        const connectHandler = mockWebsocketService.onConnect.mock.calls[0][0];
        connectHandler();
      });

      expect(mockWebsocketService.connect).toHaveBeenCalled();
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('connected');
    });

    it('should handle connection errors', async () => {
      const connectionError = new Error('Connection failed');
      mockWebsocketService.connect.mockRejectedValue(connectionError);
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      await act(async () => {
        // Simulate connection error
        const errorHandler = mockWebsocketService.onError.mock.calls[0][0];
        errorHandler(connectionError);
      });

      expect(result.current.error).toBe(connectionError);
      expect(result.current.isConnecting).toBe(false);
      expect(mockLogger.websocketError).toHaveBeenCalledWith('WebSocket error in useWebSocket hook', connectionError);
    });

    it('should handle disconnection', async () => {
      mockWebsocketService.isConnected.mockReturnValue(true);
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      await act(async () => {
        // Simulate disconnection
        const disconnectHandler = mockWebsocketService.onDisconnect.mock.calls[0][0];
        disconnectHandler();
      });

      expect(result.current.isConnected).toBe(false);
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('disconnected');
    });

    it('should cleanup on unmount', () => {
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { unmount } = renderHook(() => useWebSocketConnection());

      unmount();

      expect(mockWebsocketService.disconnect).toHaveBeenCalled();
    });

    it('should manually connect when connect is called', async () => {
      mockWebsocketService.connect.mockResolvedValue(undefined);
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      await act(async () => {
        await result.current.connect('custom-endpoint');
      });

      expect(mockWebsocketService.connect).toHaveBeenCalledWith('custom-endpoint');
    });

    it('should manually disconnect when disconnect is called', () => {
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      act(() => {
        result.current.disconnect();
      });

      expect(mockWebsocketService.disconnect).toHaveBeenCalled();
    });

    it('should send messages through the service', () => {
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      const testMessage = { type: 'test', data: 'hello' };

      act(() => {
        result.current.send(testMessage);
      });

      expect(mockWebsocketService.send).toHaveBeenCalledWith(testMessage);
    });

    it('should subscribe to topics', () => {
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      act(() => {
        result.current.subscribe('test-topic');
      });

      expect(mockWebsocketService.subscribe).toHaveBeenCalledWith('test-topic');
    });

    it('should unsubscribe from topics', () => {
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      act(() => {
        result.current.unsubscribe('test-topic');
      });

      expect(mockWebsocketService.unsubscribe).toHaveBeenCalledWith('test-topic');
    });

    it('should handle connection retry after failure', async () => {
      const connectionError = new Error('Initial connection failed');
      mockWebsocketService.connect
        .mockRejectedValueOnce(connectionError)
        .mockResolvedValueOnce(undefined);
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const { result } = renderHook(() => useWebSocketConnection());

      // First connection attempt should fail
      await act(async () => {
        try {
          await result.current.connect();
        } catch (error) {
          expect(error).toBe(connectionError);
        }
      });

      expect(result.current.error).toBe(connectionError);
      expect(mockLogger.websocketError).toHaveBeenCalledWith(
        'Failed to connect WebSocket in hook',
        connectionError
      );

      // Second connection attempt should succeed
      await act(async () => {
        await result.current.connect();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('useDashboardWebSocket', () => {
    it('should connect to dashboard endpoint', async () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});
      mockWebsocketService.isConnected.mockReturnValue(false);

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      expect(result.current.isConnected).toBe(false);
      expect(mockWebsocketService.connectToDashboard).toHaveBeenCalled();
    });

    it('should call message handler when message is received', async () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});
      mockWebsocketService.isConnected.mockReturnValue(true);

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      const testMessage: WebSocketMessage = {
        type: 'instance_update',
        timestamp: '2023-01-01T00:00:00Z',
        data: { instance_id: 'inst-1', status: 'running' },
      };

      act(() => {
        // Simulate message received
        const onMessageHandler = mockWebsocketService.onMessage.mock.calls[0][0];
        onMessageHandler(testMessage);
      });

      expect(messageHandler).toHaveBeenCalledWith(testMessage);
    });

    it('should update message handler when it changes', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler1 = jest.fn();
      const messageHandler2 = jest.fn();

      const { rerender } = renderHook(
        ({ handler }) => useDashboardWebSocket(handler),
        { initialProps: { handler: messageHandler1 } }
      );

      const testMessage: WebSocketMessage = {
        type: 'task_update',
        timestamp: '2023-01-01T00:00:00Z',
        data: { task_id: 'task-1', status: 'completed' },
      };

      // Test with first handler
      act(() => {
        const onMessageHandler = mockWebsocketService.onMessage.mock.calls[0][0];
        onMessageHandler(testMessage);
      });

      expect(messageHandler1).toHaveBeenCalledWith(testMessage);
      expect(messageHandler2).not.toHaveBeenCalled();

      // Update to second handler
      rerender({ handler: messageHandler2 });

      act(() => {
        const onMessageHandler = mockWebsocketService.onMessage.mock.calls[0][0];
        onMessageHandler(testMessage);
      });

      expect(messageHandler2).toHaveBeenCalledWith(testMessage);
    });

    it('should handle connection status changes', async () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      // Start disconnected
      mockWebsocketService.isConnected.mockReturnValue(false);

      const messageHandler = jest.fn();
      const { result, rerender } = renderHook(() => useDashboardWebSocket(messageHandler));

      expect(result.current.isConnected).toBe(false);

      // Simulate connection
      mockWebsocketService.isConnected.mockReturnValue(true);
      rerender();

      expect(result.current.isConnected).toBe(true);
    });

    it('should provide send method', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      const testMessage = { type: 'ping', timestamp: new Date().toISOString() };

      act(() => {
        result.current.send(testMessage);
      });

      expect(mockWebsocketService.send).toHaveBeenCalledWith(testMessage);
    });

    it('should provide subscribe and unsubscribe methods', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      act(() => {
        result.current.subscribe('dashboard-updates');
      });

      expect(mockWebsocketService.subscribe).toHaveBeenCalledWith('dashboard-updates');

      act(() => {
        result.current.unsubscribe('dashboard-updates');
      });

      expect(mockWebsocketService.unsubscribe).toHaveBeenCalledWith('dashboard-updates');
    });

    it('should handle dashboard connection errors', async () => {
      const dashboardError = new Error('Dashboard connection failed');
      mockWebsocketService.connectToDashboard.mockRejectedValue(dashboardError);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      await act(async () => {
        // Simulate error in dashboard connection
        const errorHandler = mockWebsocketService.onError.mock.calls[0][0];
        errorHandler(dashboardError);
      });

      expect(result.current.error).toBe(dashboardError);
    });

    it('should cleanup on unmount', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler = jest.fn();
      const { unmount } = renderHook(() => useDashboardWebSocket(messageHandler));

      unmount();

      expect(mockWebsocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('edge cases and error handling', () => {
    it('should handle message handler errors gracefully', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const faultyMessageHandler = jest.fn(() => {
        throw new Error('Handler error');
      });

      const { } = renderHook(() => useDashboardWebSocket(faultyMessageHandler));

      const testMessage: WebSocketMessage = {
        type: 'test',
        timestamp: '2023-01-01T00:00:00Z',
        data: { test: 'data' },
      };

      // This should not crash the hook
      expect(() => {
        act(() => {
          const onMessageHandler = mockWebsocketService.onMessage.mock.calls[0][0];
          onMessageHandler(testMessage);
        });
      }).not.toThrow();

      expect(faultyMessageHandler).toHaveBeenCalledWith(testMessage);
    });

    it('should handle null/undefined message handlers', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      // Test with null handler
      const { rerender } = renderHook(
        ({ handler }) => useDashboardWebSocket(handler),
        { initialProps: { handler: null as any } }
      );

      expect(() => {
        rerender({ handler: undefined as any });
      }).not.toThrow();
    });

    it('should handle rapid connection/disconnection cycles', async () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      // Simulate rapid connection/disconnection
      await act(async () => {
        const connectHandler = mockWebsocketService.onConnect.mock.calls[0][0];
        const disconnectHandler = mockWebsocketService.onDisconnect.mock.calls[0][0];

        connectHandler();
        disconnectHandler();
        connectHandler();
        disconnectHandler();
      });

      // Should handle this gracefully without errors
      expect(result.current.isConnected).toBeDefined();
    });

    it('should handle WebSocket service method failures', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      // Mock service methods to throw errors
      mockWebsocketService.send.mockImplementation(() => {
        throw new Error('Send failed');
      });
      mockWebsocketService.subscribe.mockImplementation(() => {
        throw new Error('Subscribe failed');
      });

      const messageHandler = jest.fn();
      const { result } = renderHook(() => useDashboardWebSocket(messageHandler));

      // These should not crash the hook
      expect(() => {
        act(() => {
          result.current.send({ type: 'test' });
        });
      }).not.toThrow();

      expect(() => {
        act(() => {
          result.current.subscribe('test-topic');
        });
      }).not.toThrow();
    });

    it('should handle concurrent hook instances', () => {
      mockWebsocketService.connectToDashboard.mockResolvedValue(undefined);
      mockWebsocketService.onMessage.mockReturnValue(() => {});
      mockWebsocketService.onConnect.mockReturnValue(() => {});
      mockWebsocketService.onDisconnect.mockReturnValue(() => {});
      mockWebsocketService.onError.mockReturnValue(() => {});

      const messageHandler1 = jest.fn();
      const messageHandler2 = jest.fn();

      const hook1 = renderHook(() => useDashboardWebSocket(messageHandler1));
      const hook2 = renderHook(() => useDashboardWebSocket(messageHandler2));

      // Both hooks should work independently
      const testMessage: WebSocketMessage = {
        type: 'test',
        timestamp: '2023-01-01T00:00:00Z',
        data: { test: 'data' },
      };

      act(() => {
        hook1.result.current.send(testMessage);
        hook2.result.current.send(testMessage);
      });

      expect(mockWebsocketService.send).toHaveBeenCalledTimes(2);
      expect(mockWebsocketService.send).toHaveBeenCalledWith(testMessage);

      hook1.unmount();
      hook2.unmount();
    });
  });
});
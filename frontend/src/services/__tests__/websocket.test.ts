import toast from 'react-hot-toast';
import logger from '../../utils/logger';
import { websocketService, WebSocketService } from '../websocket';
import { WebSocketMessage } from '../../types';

// Mock dependencies
jest.mock('react-hot-toast');
jest.mock('../../utils/logger');
jest.mock('../../config/environment', () => ({
  wsBaseUrl: 'ws://localhost:8080/ws',
  wsReconnectInterval: 3000,
  wsMaxReconnectAttempts: 5,
}));
jest.mock('../../validation/schemas', () => ({
  safeParseWebSocketMessage: jest.fn(),
}));

const mockToast = toast as jest.Mocked<typeof toast>;
const mockLogger = logger as jest.Mocked<typeof logger>;

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {}

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }

  // Test helpers
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  simulateClose(code: number = 1000, reason: string = 'Normal closure') {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

describe('WebSocketService', () => {
  let service: WebSocketService;
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    jest.useFakeTimers();
    
    service = new WebSocketService();
    
    // Mock the safeParseWebSocketMessage to return valid messages by default
    const { safeParseWebSocketMessage } = require('../../validation/schemas');
    safeParseWebSocketMessage.mockImplementation((data: any) => data);
  });

  afterEach(() => {
    jest.useRealTimers();
    service.cleanup();
  });

  describe('constructor', () => {
    it('should initialize with default configuration', () => {
      const newService = new WebSocketService();
      expect(newService).toBeDefined();
    });

    it('should accept custom configuration', () => {
      const config = {
        url: 'ws://custom:8080/ws',
        reconnectInterval: 5000,
        maxReconnectAttempts: 10,
        pingInterval: 60000,
        pongTimeout: 10000,
      };
      const newService = new WebSocketService(config);
      expect(newService).toBeDefined();
    });
  });

  describe('connection management', () => {
    it('should connect to WebSocket successfully', async () => {
      const connectPromise = service.connect('test-endpoint');
      
      // Get the created WebSocket instance
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      
      // Simulate successful connection
      mockWebSocket.simulateOpen();
      
      await expect(connectPromise).resolves.toBeUndefined();
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('connecting', { url: 'ws://localhost:8080/ws/test-endpoint' });
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('connected');
    });

    it('should not connect if already connecting', async () => {
      const firstConnect = service.connect('test1');
      const secondConnect = service.connect('test2');
      
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      await firstConnect;
      await secondConnect;
      
      // Should only create one WebSocket instance
      expect((global.WebSocket as any).mock.instances).toHaveLength(1);
    });

    it('should handle connection errors', async () => {
      const connectPromise = service.connect('test-endpoint');
      
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      
      // Simulate connection error
      const error = new Error('Connection failed');
      mockWebSocket.simulateError();
      
      await expect(connectPromise).rejects.toThrow('Connection failed');
      expect(mockLogger.websocketError).toHaveBeenCalledWith('Connection failed', expect.any(Error));
    });

    it('should disconnect properly', () => {
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      service.disconnect();
      
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('disconnecting');
      expect(mockWebSocket.readyState).toBe(MockWebSocket.CLOSED);
    });

    it('should return correct connection state', () => {
      expect(service.isConnected()).toBe(false);
      expect(service.getReadyState()).toBeNull();
      
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      
      expect(service.isConnected()).toBe(false); // Still connecting
      
      mockWebSocket.simulateOpen();
      expect(service.isConnected()).toBe(true);
    });
  });

  describe('message handling', () => {
    beforeEach(async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
    });

    it('should send messages when connected', () => {
      const message = { type: 'test', data: 'hello' };
      const sendSpy = jest.spyOn(mockWebSocket, 'send');
      
      service.send(message);
      
      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify(message));
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('message_sent', { type: 'test' });
    });

    it('should handle string messages', () => {
      const sendSpy = jest.spyOn(mockWebSocket, 'send');
      
      service.send('string message');
      
      expect(sendSpy).toHaveBeenCalledWith('string message');
    });

    it('should not send when disconnected', () => {
      service.disconnect();
      
      service.send({ type: 'test' });
      
      expect(mockLogger.warn).toHaveBeenCalledWith('WebSocket not connected, cannot send message');
      expect(mockToast.error).toHaveBeenCalledWith('Not connected to server');
    });

    it('should handle send errors', () => {
      const sendSpy = jest.spyOn(mockWebSocket, 'send');
      sendSpy.mockImplementation(() => {
        throw new Error('Send failed');
      });
      
      service.send({ type: 'test' });
      
      expect(mockLogger.websocketError).toHaveBeenCalledWith('Failed to send message', expect.any(Error));
    });

    it('should receive and validate messages', () => {
      const mockHandler = jest.fn();
      const unsubscribe = service.onMessage(mockHandler);
      
      const message = { type: 'test', data: 'hello' };
      mockWebSocket.simulateMessage(message);
      
      expect(mockHandler).toHaveBeenCalledWith(message);
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('message_received', { type: 'test' });
      
      unsubscribe();
    });

    it('should ignore invalid messages', () => {
      const { safeParseWebSocketMessage } = require('../../validation/schemas');
      safeParseWebSocketMessage.mockReturnValue(null);
      
      const mockHandler = jest.fn();
      service.onMessage(mockHandler);
      
      mockWebSocket.simulateMessage({ invalid: 'message' });
      
      expect(mockHandler).not.toHaveBeenCalled();
      expect(mockLogger.warn).toHaveBeenCalledWith('Received invalid WebSocket message, ignoring');
    });

    it('should handle message parsing errors', () => {
      const mockHandler = jest.fn();
      service.onMessage(mockHandler);
      
      // Simulate invalid JSON
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(new MessageEvent('message', { data: 'invalid json' }));
      }
      
      expect(mockHandler).not.toHaveBeenCalled();
      expect(mockLogger.websocketError).toHaveBeenCalledWith('Failed to parse message', expect.any(Error));
    });

    it('should handle pong messages', () => {
      const message = { type: 'pong', timestamp: new Date().toISOString() };
      mockWebSocket.simulateMessage(message);
      
      // Pong messages should not be passed to handlers
      const mockHandler = jest.fn();
      service.onMessage(mockHandler);
      mockWebSocket.simulateMessage(message);
      
      expect(mockHandler).not.toHaveBeenCalled();
    });
  });

  describe('subscription management', () => {
    beforeEach(async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
    });

    it('should send subscribe message', () => {
      const sendSpy = jest.spyOn(mockWebSocket, 'send');
      
      service.subscribe('test-topic');
      
      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"type":"subscribe"')
      );
      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"topic":"test-topic"')
      );
    });

    it('should send unsubscribe message', () => {
      const sendSpy = jest.spyOn(mockWebSocket, 'send');
      
      service.unsubscribe('test-topic');
      
      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"type":"unsubscribe"')
      );
      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"topic":"test-topic"')
      );
    });
  });

  describe('event handler registration', () => {
    it('should register and unregister message handlers', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();
      
      const unsubscribe1 = service.onMessage(handler1);
      const unsubscribe2 = service.onMessage(handler2);
      
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      const message = { type: 'test', data: 'hello' };
      mockWebSocket.simulateMessage(message);
      
      expect(handler1).toHaveBeenCalledWith(message);
      expect(handler2).toHaveBeenCalledWith(message);
      
      unsubscribe1();
      mockWebSocket.simulateMessage(message);
      
      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(2);
    });

    it('should register connect handlers', () => {
      const connectHandler = jest.fn();
      service.onConnect(connectHandler);
      
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      expect(connectHandler).toHaveBeenCalled();
    });

    it('should register disconnect handlers', () => {
      const disconnectHandler = jest.fn();
      service.onDisconnect(disconnectHandler);
      
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      mockWebSocket.simulateClose();
      
      expect(disconnectHandler).toHaveBeenCalled();
    });

    it('should register error handlers', () => {
      const errorHandler = jest.fn();
      service.onError(errorHandler);
      
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateError();
      
      expect(errorHandler).toHaveBeenCalled();
    });

    it('should handle errors in message handlers gracefully', () => {
      const errorHandler = jest.fn(() => {
        throw new Error('Handler error');
      });
      const normalHandler = jest.fn();
      
      service.onMessage(errorHandler);
      service.onMessage(normalHandler);
      
      service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      const message = { type: 'test', data: 'hello' };
      mockWebSocket.simulateMessage(message);
      
      expect(errorHandler).toHaveBeenCalled();
      expect(normalHandler).toHaveBeenCalled();
      expect(mockLogger.error).toHaveBeenCalledWith('WebSocket message handler error', expect.any(Error));
    });
  });

  describe('reconnection logic', () => {
    it('should attempt reconnection on unexpected close', async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      // Simulate unexpected close (not code 1000)
      mockWebSocket.simulateClose(1006, 'Connection lost');
      
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('disconnected', { code: 1006, reason: 'Connection lost' });
      
      // Fast forward to trigger reconnection
      jest.advanceTimersByTime(3000);
      
      expect(mockLogger.websocketEvent).toHaveBeenCalledWith('reconnecting', { attempt: 1, max: 5 });
    });

    it('should not reconnect on normal close', async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      // Simulate normal close (code 1000)
      mockWebSocket.simulateClose(1000, 'Normal closure');
      
      jest.advanceTimersByTime(5000);
      
      // Should not attempt reconnection
      expect(mockLogger.websocketEvent).not.toHaveBeenCalledWith('reconnecting', expect.any(Object));
    });

    it('should stop reconnecting after max attempts', async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      // Simulate unexpected close
      mockWebSocket.simulateClose(1006, 'Connection lost');
      
      // Simulate multiple failed reconnection attempts
      for (let i = 0; i < 6; i++) {
        jest.advanceTimersByTime(3000);
        if ((global.WebSocket as any).mock.instances.length > i + 1) {
          mockWebSocket = (global.WebSocket as any).mock.instances[i + 1];
          mockWebSocket.simulateClose(1006, 'Still failing');
        }
      }
      
      expect(mockLogger.error).toHaveBeenCalledWith('Max reconnection attempts reached');
      expect(mockToast.error).toHaveBeenCalledWith('Connection lost - please refresh the page');
    });

    it('should reset reconnect attempts on successful reconnection', async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      // Simulate close and reconnection
      mockWebSocket.simulateClose(1006, 'Connection lost');
      jest.advanceTimersByTime(3000);
      
      // Simulate successful reconnection
      mockWebSocket = (global.WebSocket as any).mock.instances[1];
      mockWebSocket.simulateOpen();
      
      expect(mockToast.success).toHaveBeenCalledWith('Reconnected to server');
    });
  });

  describe('ping/pong mechanism', () => {
    beforeEach(async () => {
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
    });

    it('should send ping messages periodically', () => {
      const sendSpy = jest.spyOn(mockWebSocket, 'send');
      
      // Fast forward to trigger ping
      jest.advanceTimersByTime(30000);
      
      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"type":"ping"')
      );
    });

    it('should handle pong timeout', () => {
      const closeSpy = jest.spyOn(mockWebSocket, 'close');
      
      // Trigger ping
      jest.advanceTimersByTime(30000);
      
      // Don't send pong response, trigger timeout
      jest.advanceTimersByTime(5000);
      
      expect(mockLogger.warn).toHaveBeenCalledWith('Pong timeout - connection may be stale');
      expect(closeSpy).toHaveBeenCalledWith(1006, 'Pong timeout');
    });

    it('should clear pong timeout on pong response', () => {
      // Trigger ping
      jest.advanceTimersByTime(30000);
      
      // Send pong response
      const pongMessage = { type: 'pong', timestamp: new Date().toISOString() };
      mockWebSocket.simulateMessage(pongMessage);
      
      // Fast forward past pong timeout - should not close
      jest.advanceTimersByTime(6000);
      
      expect(mockLogger.warn).not.toHaveBeenCalledWith('Pong timeout - connection may be stale');
    });
  });

  describe('specialized connection methods', () => {
    it('should connect to dashboard endpoint', async () => {
      const connectPromise = service.connectToDashboard();
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      await connectPromise;
      
      expect(mockWebSocket.url).toBe('ws://localhost:8080/ws/dashboard');
    });

    it('should connect to instance endpoint', async () => {
      const connectPromise = service.connectToInstance('instance-123');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      await connectPromise;
      
      expect(mockWebSocket.url).toBe('ws://localhost:8080/ws/instances/instance-123');
    });

    it('should connect to task endpoint', async () => {
      const connectPromise = service.connectToTask('task-456');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      await connectPromise;
      
      expect(mockWebSocket.url).toBe('ws://localhost:8080/ws/tasks/task-456');
    });

    it('should connect to logs endpoint', async () => {
      const connectPromise = service.connectToLogs();
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      await connectPromise;
      
      expect(mockWebSocket.url).toBe('ws://localhost:8080/ws/logs');
    });
  });

  describe('cleanup', () => {
    it('should clear all handlers and disconnect on cleanup', async () => {
      const messageHandler = jest.fn();
      const connectHandler = jest.fn();
      const disconnectHandler = jest.fn();
      const errorHandler = jest.fn();
      
      service.onMessage(messageHandler);
      service.onConnect(connectHandler);
      service.onDisconnect(disconnectHandler);
      service.onError(errorHandler);
      
      await service.connect('test-endpoint');
      mockWebSocket = (global.WebSocket as any).mock.instances[0];
      mockWebSocket.simulateOpen();
      
      service.cleanup();
      
      // Verify handlers are cleared and connection is closed
      expect(service.isConnected()).toBe(false);
      
      // Simulate events after cleanup - handlers should not be called
      mockWebSocket.simulateMessage({ type: 'test' });
      mockWebSocket.simulateOpen();
      
      expect(messageHandler).not.toHaveBeenCalled();
      expect(connectHandler).not.toHaveBeenCalled();
    });
  });

  describe('singleton export', () => {
    it('should export a singleton instance', () => {
      expect(websocketService).toBeInstanceOf(WebSocketService);
    });
  });
});
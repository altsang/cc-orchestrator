// WebSocket service for real-time communication with CC-Orchestrator backend

import toast from 'react-hot-toast';
import { wsBaseUrl, wsReconnectInterval, wsMaxReconnectAttempts } from '../config/environment';
import { safeParseWebSocketMessage } from '../validation/schemas';
import logger from '../utils/logger';
import type { WebSocketMessage } from '../types';

export interface WebSocketConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
  pongTimeout?: number;
}

export type MessageHandler = (message: WebSocketMessage) => void;
export type ConnectionHandler = () => void;
export type ErrorHandler = (error: Event | Error) => void;

export class WebSocketService {
  private socket: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private messageHandlers = new Set<MessageHandler>();
  private connectHandlers = new Set<ConnectionHandler>();
  private disconnectHandlers = new Set<ConnectionHandler>();
  private errorHandlers = new Set<ErrorHandler>();

  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;
  private pongTimer: NodeJS.Timeout | null = null;

  private isConnecting = false;
  private isReconnecting = false;
  private shouldReconnect = true;

  constructor(config: WebSocketConfig = {}) {
    this.config = {
      url: wsBaseUrl,
      reconnectInterval: wsReconnectInterval,
      maxReconnectAttempts: wsMaxReconnectAttempts,
      pingInterval: 30000,
      pongTimeout: 5000,
      ...config,
    };
  }

  // Connection management
  async connect(endpoint: string = 'connect'): Promise<void> {
    if (this.isConnecting || (this.socket && this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isConnecting = true;
    this.shouldReconnect = true;

    const wsUrl = `${this.config.url}/${endpoint}`;
    logger.websocketEvent('connecting', { url: wsUrl });

    try {
      this.socket = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      logger.websocketError('Connection failed', error as Error);
      this.isConnecting = false;
      this.handleError(error as Error);
      throw error;
    }
  }

  disconnect(): void {
    logger.websocketEvent('disconnecting');
    this.shouldReconnect = false;
    this.clearTimers();

    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }

    this.reconnectAttempts = 0;
  }

  // Connection state
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  getReadyState(): number | null {
    return this.socket?.readyState ?? null;
  }

  // Message handling
  send(message: any): void {
    if (!this.isConnected()) {
      logger.warn('WebSocket not connected, cannot send message');
      toast.error('Not connected to server');
      return;
    }

    try {
      const payload = typeof message === 'string' ? message : JSON.stringify(message);
      this.socket!.send(payload);
      logger.websocketEvent('message_sent', { type: message.type });
    } catch (error) {
      logger.websocketError('Failed to send message', error as Error);
      this.handleError(error as Error);
    }
  }

  // Subscription management
  subscribe(topic: string): void {
    this.send({
      type: 'subscribe',
      topic,
      timestamp: new Date().toISOString(),
    });
  }

  unsubscribe(topic: string): void {
    this.send({
      type: 'unsubscribe',
      topic,
      timestamp: new Date().toISOString(),
    });
  }

  // Event handler registration
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.connectHandlers.add(handler);
    return () => this.connectHandlers.delete(handler);
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectHandlers.add(handler);
    return () => this.disconnectHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  // Private methods
  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.onopen = (event) => {
      logger.websocketEvent('connected');
      this.isConnecting = false;
      this.isReconnecting = false;
      this.reconnectAttempts = 0;

      this.startPingTimer();

      // Notify handlers
      this.connectHandlers.forEach(handler => handler());

      if (this.reconnectAttempts > 0) {
        toast.success('Reconnected to server');
      }
    };

    this.socket.onmessage = (event) => {
      try {
        // Parse and validate the message
        const rawMessage = JSON.parse(event.data);
        const message = safeParseWebSocketMessage(rawMessage);

        if (!message) {
          logger.warn('Received invalid WebSocket message, ignoring');
          return;
        }

        logger.websocketEvent('message_received', { type: message.type });

        // Handle pong messages
        if (message.type === 'pong') {
          this.handlePong();
          return;
        }

        // Notify message handlers with validated message
        this.messageHandlers.forEach(handler => {
          try {
            handler(message);
          } catch (handlerError) {
            logger.error('WebSocket message handler error', handlerError as Error);
          }
        });
      } catch (error) {
        logger.websocketError('Failed to parse message', error as Error);
      }
    };

    this.socket.onclose = (event) => {
      logger.websocketEvent('disconnected', { code: event.code, reason: event.reason });
      this.isConnecting = false;
      this.clearTimers();

      // Notify handlers
      this.disconnectHandlers.forEach(handler => handler());

      // Attempt reconnection if needed
      if (this.shouldReconnect && event.code !== 1000) {
        this.attemptReconnection();
      }
    };

    this.socket.onerror = (error) => {
      logger.websocketError('WebSocket error event', error);
      this.isConnecting = false;
      this.handleError(error);
    };
  }

  private attemptReconnection(): void {
    if (this.isReconnecting || this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
        logger.error('Max reconnection attempts reached');
        toast.error('Connection lost - please refresh the page');
      }
      return;
    }

    this.isReconnecting = true;
    this.reconnectAttempts++;

    logger.websocketEvent('reconnecting', {
      attempt: this.reconnectAttempts,
      max: this.config.maxReconnectAttempts
    });

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(error => {
        logger.websocketError('Reconnection failed', error);
        this.isReconnecting = false;

        // Try again after interval
        if (this.shouldReconnect) {
          setTimeout(() => this.attemptReconnection(), this.config.reconnectInterval);
        }
      });
    }, this.config.reconnectInterval);
  }

  private startPingTimer(): void {
    this.clearPingTimer();

    this.pingTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: 'ping',
          timestamp: new Date().toISOString(),
        });

        // Start pong timeout
        this.pongTimer = setTimeout(() => {
          logger.warn('Pong timeout - connection may be stale');
          this.socket?.close(1006, 'Pong timeout');
        }, this.config.pongTimeout);
      }
    }, this.config.pingInterval);
  }

  private handlePong(): void {
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  private clearTimers(): void {
    this.clearReconnectTimer();
    this.clearPingTimer();
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }

    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  private handleError(error: Event | Error): void {
    logger.websocketError('WebSocket service error', error);
    this.errorHandlers.forEach(handler => handler(error));
  }

  // Specialized connection methods for different endpoints
  async connectToDashboard(): Promise<void> {
    return this.connect('dashboard');
  }

  async connectToInstance(instanceId: string): Promise<void> {
    return this.connect(`instances/${instanceId}`);
  }

  async connectToTask(taskId: string): Promise<void> {
    return this.connect(`tasks/${taskId}`);
  }

  async connectToLogs(): Promise<void> {
    return this.connect('logs');
  }

  // Cleanup method for component unmounting
  cleanup(): void {
    this.messageHandlers.clear();
    this.connectHandlers.clear();
    this.disconnectHandlers.clear();
    this.errorHandlers.clear();
    this.disconnect();
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
export default websocketService;

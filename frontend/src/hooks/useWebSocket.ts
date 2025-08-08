// React hook for WebSocket connection management

import { useEffect, useRef, useCallback } from 'react';
import websocketService, { MessageHandler, ConnectionHandler, ErrorHandler } from '../services/websocket';
import type { WebSocketMessage } from '../types';

export interface UseWebSocketOptions {
  endpoint?: string;
  autoConnect?: boolean;
  subscribeToTopics?: string[];
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  connect: (endpoint?: string) => Promise<void>;
  disconnect: () => void;
  send: (message: any) => void;
  subscribe: (topic: string) => void;
  unsubscribe: (topic: string) => void;
  lastMessage: WebSocketMessage | null;
}

export function useWebSocket(
  onMessage?: MessageHandler,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    endpoint = 'connect',
    autoConnect = true,
    subscribeToTopics = [],
  } = options;

  const lastMessageRef = useRef<WebSocketMessage | null>(null);
  const isConnectedRef = useRef(false);
  const subscribedTopicsRef = useRef(new Set<string>());

  // Update connection state
  const updateConnectionState = useCallback(() => {
    isConnectedRef.current = websocketService.isConnected();
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((message: WebSocketMessage) => {
    lastMessageRef.current = message;
    onMessage?.(message);
  }, [onMessage]);

  // Handle connection events
  const handleConnect = useCallback(() => {
    console.log('WebSocket connected in useWebSocket hook');
    updateConnectionState();
    
    // Auto-subscribe to topics
    subscribeToTopics.forEach(topic => {
      websocketService.subscribe(topic);
      subscribedTopicsRef.current.add(topic);
    });
  }, [subscribeToTopics, updateConnectionState]);

  const handleDisconnect = useCallback(() => {
    console.log('WebSocket disconnected in useWebSocket hook');
    updateConnectionState();
    subscribedTopicsRef.current.clear();
  }, [updateConnectionState]);

  const handleError = useCallback((error: Event | Error) => {
    console.error('WebSocket error in useWebSocket hook:', error);
    updateConnectionState();
  }, [updateConnectionState]);

  // Connect function
  const connect = useCallback(async (connectEndpoint?: string) => {
    try {
      await websocketService.connect(connectEndpoint || endpoint);
    } catch (error) {
      console.error('Failed to connect WebSocket in hook:', error);
    }
  }, [endpoint]);

  // Disconnect function
  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  // Send function
  const send = useCallback((message: any) => {
    websocketService.send(message);
  }, []);

  // Subscribe function
  const subscribe = useCallback((topic: string) => {
    websocketService.subscribe(topic);
    subscribedTopicsRef.current.add(topic);
  }, []);

  // Unsubscribe function
  const unsubscribe = useCallback((topic: string) => {
    websocketService.unsubscribe(topic);
    subscribedTopicsRef.current.delete(topic);
  }, []);

  // Setup and cleanup effects
  useEffect(() => {
    // Register event handlers
    const unsubscribeMessage = websocketService.onMessage(handleMessage);
    const unsubscribeConnect = websocketService.onConnect(handleConnect);
    const unsubscribeDisconnect = websocketService.onDisconnect(handleDisconnect);
    const unsubscribeError = websocketService.onError(handleError);

    // Auto-connect if enabled
    if (autoConnect && !websocketService.isConnected()) {
      connect();
    }

    // Cleanup function
    return () => {
      unsubscribeMessage();
      unsubscribeConnect();
      unsubscribeDisconnect();
      unsubscribeError();
    };
  }, [autoConnect, connect, handleMessage, handleConnect, handleDisconnect, handleError]);

  return {
    isConnected: isConnectedRef.current,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    lastMessage: lastMessageRef.current,
  };
}

// Specialized hooks for different connection types
export function useDashboardWebSocket(onMessage?: MessageHandler) {
  return useWebSocket(onMessage, {
    endpoint: 'dashboard',
    autoConnect: true,
    subscribeToTopics: ['dashboard', 'instances', 'tasks', 'system_status', 'alerts'],
  });
}

export function useInstanceWebSocket(instanceId: string, onMessage?: MessageHandler) {
  return useWebSocket(onMessage, {
    endpoint: `instances/${instanceId}`,
    autoConnect: true,
    subscribeToTopics: [`instance:${instanceId}`],
  });
}

export function useTaskWebSocket(taskId: string, onMessage?: MessageHandler) {
  return useWebSocket(onMessage, {
    endpoint: `tasks/${taskId}`,
    autoConnect: true,
    subscribeToTopics: [`task:${taskId}`],
  });
}

export function useLogsWebSocket(onMessage?: MessageHandler) {
  return useWebSocket(onMessage, {
    endpoint: 'logs',
    autoConnect: true,
    subscribeToTopics: ['logs'],
  });
}
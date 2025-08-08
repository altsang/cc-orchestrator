import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { WebSocketMessage } from '../types'

interface WebSocketContextType {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  subscribe: (eventTypes: string[]) => void
  unsubscribe: (eventTypes: string[]) => void
  sendMessage: (message: any) => void
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const maxReconnectAttempts = 5

  const wsUrl = import.meta.env.DEV ? 'ws://localhost:8000/ws/dashboard' : `ws://${window.location.host}/ws/dashboard`

  const connect = useCallback(() => {
    try {
      const websocket = new WebSocket(wsUrl)

      websocket.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setReconnectAttempts(0)

        // Send initial ping
        websocket.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }))
      }

      websocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)

          if (message.type === 'pong') {
            console.log('WebSocket heartbeat received')
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      websocket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.reason)
        setIsConnected(false)
        setWs(null)

        // Attempt to reconnect if not intentional close
        if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
          const timeout = Math.pow(2, reconnectAttempts) * 1000 // Exponential backoff
          console.log(`Attempting to reconnect in ${timeout}ms`)

          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1)
            connect()
          }, timeout)
        }
      }

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }

      setWs(websocket)
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [wsUrl, reconnectAttempts])

  useEffect(() => {
    connect()

    return () => {
      if (ws) {
        ws.close(1000, 'Component unmounting')
      }
    }
  }, [])

  // Heartbeat to keep connection alive
  useEffect(() => {
    if (!isConnected || !ws) return

    const interval = setInterval(() => {
      ws.send(JSON.stringify({
        type: 'ping',
        timestamp: new Date().toISOString()
      }))
    }, 30000) // 30 seconds

    return () => clearInterval(interval)
  }, [isConnected, ws])

  const subscribe = useCallback((eventTypes: string[]) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify({
        type: 'subscribe',
        events: eventTypes
      }))
    }
  }, [ws, isConnected])

  const unsubscribe = useCallback((eventTypes: string[]) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify({
        type: 'unsubscribe',
        events: eventTypes
      }))
    }
  }, [ws, isConnected])

  const sendMessage = useCallback((message: any) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify(message))
    }
  }, [ws, isConnected])

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        lastMessage,
        subscribe,
        unsubscribe,
        sendMessage,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

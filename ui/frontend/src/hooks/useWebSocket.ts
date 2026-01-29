import { useEffect, useRef, useCallback } from 'react'
import { useDashboardStore } from '@/context/DashboardStore'
import { WebSocketMessage } from '@/types'

const WS_URL = `ws://${window.location.host}/ws`
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 5

export const useWebSocket = () => {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null)
  
  const { 
    setWebSocketConnected, 
    setWebSocketMessage,
    setDashboardData,
  } = useDashboardStore()
  
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return
    }
    
    try {
      ws.current = new WebSocket(WS_URL)
      
      ws.current.onopen = () => {
        console.log('[WebSocket] Connected')
        setWebSocketConnected(true)
        reconnectAttempts.current = 0
        
        // Send initial ping
        ws.current?.send(JSON.stringify({ type: 'ping' }))
      }
      
      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setWebSocketMessage(message)
          
          // Handle different message types
          switch (message.type) {
            case 'status':
              if (message.data) {
                // Update dashboard data with real-time status
                const currentData = useDashboardStore.getState().dashboardData
                if (currentData) {
                  setDashboardData({
                    ...currentData,
                    bot: message.data.bot || currentData.bot,
                    performance: message.data.performance || currentData.performance,
                    last_updated: new Date().toISOString(),
                  })
                }
              }
              break
              
            case 'trade':
              // Invalidate trades query to refresh
              break
              
            case 'market':
              // Handle market updates
              break
              
            case 'ping':
              // Keep connection alive
              break
          }
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error)
        }
      }
      
      ws.current.onclose = () => {
        console.log('[WebSocket] Disconnected')
        setWebSocketConnected(false)
        
        // Attempt reconnection
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++
          console.log(`[WebSocket] Reconnecting... (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`)
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
        }
      }
      
      ws.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
      }
    } catch (error) {
      console.error('[WebSocket] Connection error:', error)
    }
  }, [setWebSocketConnected, setWebSocketMessage, setDashboardData])
  
  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
    
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
  }, [])
  
  const send = useCallback((data: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    } else {
      console.warn('[WebSocket] Cannot send, connection not open')
    }
  }, [])
  
  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])
  
  return { connect, disconnect, send }
}

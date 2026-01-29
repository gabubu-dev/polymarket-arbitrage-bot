import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { DashboardData, Trade, MarketData, BotStatus, PerformanceStats } from '@/types'

const API_BASE = '/api'

// Axios instance with defaults
const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Dashboard API
export const useDashboardData = () => {
  return useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data } = await api.get('/status')
      return {
        bot: data.bot,
        performance: data.performance,
        paper_trading: data.paper_trading || {
          enabled: false,
          virtual_balance: 10000,
          initial_balance: 10000,
          positions: [],
        },
        last_updated: new Date().toISOString(),
      }
    },
    refetchInterval: 30000, // 30 seconds
    staleTime: 25000,
  })
}

// Trades API
export const useTrades = (limit = 50) => {
  return useQuery<Trade[]>({
    queryKey: ['trades', limit],
    queryFn: async () => {
      const { data } = await api.get('/trades', { params: { limit } })
      return data
    },
    refetchInterval: 30000,
  })
}

// Markets API
export const useMarkets = () => {
  return useQuery<MarketData[]>({
    queryKey: ['markets'],
    queryFn: async () => {
      // This endpoint might not exist in current backend, return mock data
      const { data } = await api.get('/markets').catch(() => ({ data: getMockMarketData() }))
      return data
    },
    refetchInterval: 10000, // Markets update more frequently
  })
}

// Bot Control Mutations
export const useBotControl = () => {
  const queryClient = useQueryClient()
  
  return {
    start: useMutation({
      mutationFn: () => api.post('/control/start'),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      },
    }),
    
    stop: useMutation({
      mutationFn: () => api.post('/control/stop'),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      },
    }),
    
    restart: useMutation({
      mutationFn: () => api.post('/control/restart'),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      },
    }),
  }
}

// Logs API
export const useLogs = (lines = 100) => {
  return useQuery<string[]>({
    queryKey: ['logs', lines],
    queryFn: async () => {
      const { data } = await api.get('/logs', { params: { lines } })
      return data.logs || []
    },
    refetchInterval: 5000,
  })
}

// Mock data helpers
function getMockMarketData(): MarketData[] {
  return [
    { symbol: 'BTC/USDT', polymarket_price: 43500, exchange_price: 43450, divergence: 0.11, opportunity: true, last_updated: new Date().toISOString() },
    { symbol: 'ETH/USDT', polymarket_price: 2580, exchange_price: 2585, divergence: -0.19, opportunity: false, last_updated: new Date().toISOString() },
    { symbol: 'SOL/USDT', polymarket_price: 102.5, exchange_price: 102.3, divergence: 0.20, opportunity: true, last_updated: new Date().toISOString() },
    { symbol: 'ARB/USDT', polymarket_price: 1.85, exchange_price: 1.87, divergence: -1.07, opportunity: false, last_updated: new Date().toISOString() },
    { symbol: 'OP/USDT', polymarket_price: 3.42, exchange_price: 3.40, divergence: 0.59, opportunity: false, last_updated: new Date().toISOString() },
  ]
}

export default api

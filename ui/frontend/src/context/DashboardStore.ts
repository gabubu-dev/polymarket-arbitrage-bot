import { create } from 'zustand'
import { DashboardData, Trade, MarketData, WebSocketMessage } from '@/types'

interface DashboardState {
  // Data
  dashboardData: DashboardData | null
  trades: Trade[]
  markets: MarketData[]
  
  // UI State
  selectedTab: 'dashboard' | 'trades' | 'markets' | 'config' | 'logs'
  isLoading: boolean
  error: string | null
  
  // Real-time
  lastWebSocketMessage: WebSocketMessage | null
  isWebSocketConnected: boolean
  
  // Actions
  setDashboardData: (data: DashboardData) => void
  setTrades: (trades: Trade[]) => void
  setMarkets: (markets: MarketData[]) => void
  setSelectedTab: (tab: DashboardState['selectedTab']) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setWebSocketMessage: (message: WebSocketMessage) => void
  setWebSocketConnected: (connected: boolean) => void
  
  // Computed
  getPaperTradingPnl: () => number
  getPaperTradingPnlPercent: () => number
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
  dashboardData: null,
  trades: [],
  markets: [],
  selectedTab: 'dashboard',
  isLoading: true,
  error: null,
  lastWebSocketMessage: null,
  isWebSocketConnected: false,
  
  // Actions
  setDashboardData: (data) => set({ dashboardData: data, isLoading: false, error: null }),
  setTrades: (trades) => set({ trades }),
  setMarkets: (markets) => set({ markets }),
  setSelectedTab: (tab) => set({ selectedTab: tab }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  setWebSocketMessage: (message) => set({ lastWebSocketMessage: message }),
  setWebSocketConnected: (connected) => set({ isWebSocketConnected: connected }),
  
  // Computed getters
  getPaperTradingPnl: () => {
    const { dashboardData } = get()
    if (!dashboardData?.paper_trading) return 0
    return dashboardData.paper_trading.virtual_balance - dashboardData.paper_trading.initial_balance
  },
  
  getPaperTradingPnlPercent: () => {
    const { dashboardData } = get()
    if (!dashboardData?.paper_trading || dashboardData.paper_trading.initial_balance === 0) return 0
    const pnl = dashboardData.paper_trading.virtual_balance - dashboardData.paper_trading.initial_balance
    return (pnl / dashboardData.paper_trading.initial_balance) * 100
  },
}))

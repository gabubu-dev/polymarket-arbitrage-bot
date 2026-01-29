export interface BotStatus {
  running: boolean
  pid: number | null
  uptime_seconds: number | null
  cpu_percent: number | null
  memory_mb: number | null
}

export interface PaperTradingStatus {
  enabled: boolean
  virtual_balance: number
  initial_balance: number
  positions: Position[]
}

export interface PerformanceStats {
  daily_pnl: number
  weekly_pnl: number
  all_time_pnl: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  open_positions: number
}

export interface DashboardData {
  bot: BotStatus
  performance: PerformanceStats
  paper_trading: PaperTradingStatus
  last_updated: string
}

export interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  size_usd: number
  entry_price: number
  current_price: number
  pnl: number
  pnl_percent: number
  opened_at: string
}

export interface Trade {
  id: string
  timestamp: string
  symbol: string
  side: 'buy' | 'sell'
  size_usd: number
  entry_price: number
  exit_price?: number
  pnl?: number
  status: 'open' | 'closed'
  strategy: string
}

export interface MarketData {
  symbol: string
  polymarket_price: number
  exchange_price: number
  divergence: number
  opportunity: boolean
  last_updated: string
}

export interface ArbitrageOpportunity {
  id: string
  symbol: string
  buy_exchange: string
  sell_exchange: string
  buy_price: number
  sell_price: number
  spread: number
  spread_percent: number
  estimated_profit: number
  timestamp: string
}

export interface WhaleActivity {
  id: string
  timestamp: string
  symbol: string
  type: 'buy' | 'sell'
  size_usd: number
  price: number
  wallet: string
}

export interface ChartDataPoint {
  timestamp: string
  value: number
  label?: string
}

export interface PortfolioChartData {
  labels: string[]
  values: number[]
  pnl: number[]
}

export interface WebSocketMessage {
  type: 'status' | 'trade' | 'market' | 'whale' | 'ping'
  data: unknown
  timestamp: string
}

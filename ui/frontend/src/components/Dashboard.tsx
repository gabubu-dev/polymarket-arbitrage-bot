import React from 'react'
import { useDashboardData, useTrades } from '@/hooks/useApi'
import { useDashboardStore } from '@/context/DashboardStore'
import { StatCard } from './StatCard'
import { ChartPanel } from './ChartPanel'
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Activity,
  BarChart3,
  Wallet,
  Percent
} from 'lucide-react'

// Generate mock portfolio data
const generatePortfolioData = () => {
  const data = []
  let value = 10000
  const now = new Date()
  
  for (let i = 30; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    
    const change = (Math.random() - 0.4) * 200
    value += change
    
    data.push({
      name: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.max(value, 5000),
      pnl: value - 10000,
    })
  }
  return data
}

// Generate mock trading activity data
const generateTradingData = () => {
  const data = []
  const now = new Date()
  
  for (let i = 14; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    
    data.push({
      name: date.toLocaleDateString('en-US', { weekday: 'short' }),
      trades: Math.floor(Math.random() * 15) + 2,
      profit: (Math.random() - 0.3) * 100,
    })
  }
  return data
}

// Generate mock whale activity data
const generateWhaleData = () => {
  return [
    { name: 'Mon', buys: 45000, sells: 32000 },
    { name: 'Tue', buys: 52000, sells: 28000 },
    { name: 'Wed', buys: 38000, sells: 41000 },
    { name: 'Thu', buys: 61000, sells: 35000 },
    { name: 'Fri', buys: 48000, sells: 52000 },
    { name: 'Sat', buys: 33000, sells: 29000 },
    { name: 'Sun', buys: 42000, sells: 38000 },
  ]
}

// Generate mock arbitrage data
const generateArbitrageData = () => {
  return [
    { name: 'BTC/USDT', opportunities: 12, profit: 145.50 },
    { name: 'ETH/USDT', opportunities: 8, profit: 89.20 },
    { name: 'SOL/USDT', opportunities: 15, profit: 67.80 },
    { name: 'ARB/USDT', opportunities: 5, profit: 23.40 },
    { name: 'OP/USDT', opportunities: 3, profit: 12.60 },
  ]
}

export const Dashboard: React.FC = () => {
  const { data: dashboardData, isLoading } = useDashboardData()
  const { data: trades } = useTrades(10)
  const { getPaperTradingPnl, getPaperTradingPnlPercent } = useDashboardStore()
  
  const performance = dashboardData?.performance
  const pnl = getPaperTradingPnl()
  const pnlPercent = getPaperTradingPnlPercent()
  const isPnlPositive = pnl >= 0
  
  // Chart data
  const portfolioData = React.useMemo(() => generatePortfolioData(), [dashboardData?.last_updated])
  const tradingData = React.useMemo(() => generateTradingData(), [dashboardData?.last_updated])
  const whaleData = React.useMemo(() => generateWhaleData(), [])
  const arbitrageData = React.useMemo(() => generateArbitrageData(), [])

  return (
    <div className="p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Open Positions"
          value={performance?.open_positions ?? '-'}
          subtitle="Active trades"
          icon={<Target className="w-5 h-5" />}
          loading={isLoading}
        />
        
        <StatCard
          title="Total P&L"
          value={performance ? `$${performance.all_time_pnl.toFixed(2)}` : '-'}
          subtitle={performance ? `${performance.all_time_pnl >= 0 ? '+' : ''}${performance.all_time_pnl.toFixed(2)} USD` : undefined}
          trend={performance ? (performance.all_time_pnl >= 0 ? 'up' : 'down') : 'neutral'}
          icon={<Wallet className="w-5 h-5" />}
          loading={isLoading}
        />
        
        <StatCard
          title="Win Rate"
          value={performance ? `${performance.win_rate.toFixed(1)}%` : '-'}
          subtitle={performance ? `${performance.winning_trades}W / ${performance.losing_trades}L` : undefined}
          icon={<Percent className="w-5 h-5" />}
          loading={isLoading}
        />
        
        <StatCard
          title="Total Trades"
          value={performance?.total_trades ?? '-'}
          subtitle="All time"
          icon={<BarChart3 className="w-5 h-5" />}
          loading={isLoading}
        />
      </div>
      
      {/* Paper Trading Stats (if enabled) */}
      {dashboardData?.paper_trading?.enabled && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            title="Virtual Balance"
            value={`$${dashboardData.paper_trading.virtual_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
            subtitle="Paper trading"
            icon={<Wallet className="w-5 h-5" />}
            loading={isLoading}
          />
          
          <StatCard
            title="Virtual P&L"
            value={`${isPnlPositive ? '+' : ''}$${pnl.toFixed(2)}`}
            subtitle={`${isPnlPositive ? '+' : ''}${pnlPercent.toFixed(2)}%`}
            trend={isPnlPositive ? 'up' : 'down'}
            icon={isPnlPositive ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
            loading={isLoading}
          />
          
          <StatCard
            title="Daily P&L"
            value={performance ? `$${performance.daily_pnl.toFixed(2)}` : '-'}
            subtitle="Last 24 hours"
            trend={performance ? (performance.daily_pnl >= 0 ? 'up' : 'down') : 'neutral'}
            icon={<Activity className="w-5 h-5" />}
            loading={isLoading}
          />
        </div>
      )}
      
      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPanel
          title="Portfolio Overview"
          type="area"
          data={portfolioData}
          dataKey="value"
          xAxisKey="name"
          loading={isLoading}
        />
        
        <ChartPanel
          title="Trading Activity"
          type="bar"
          data={tradingData}
          dataKey="trades"
          xAxisKey="name"
          loading={isLoading}
        />
        
        <ChartPanel
          title="Whale Activity"
          type="line"
          data={whaleData}
          dataKey="buys"
          xAxisKey="name"
          loading={isLoading}
          multiSeries={[
            { key: 'buys', name: 'Large Buys', color: '#00ff88' },
            { key: 'sells', name: 'Large Sells', color: '#ff6b6b' },
          ]}
        />
        
        <ChartPanel
          title="Arbitrage Opportunities"
          type="bar"
          data={arbitrageData}
          dataKey="opportunities"
          xAxisKey="name"
          loading={isLoading}
        />
      </div>
      
      {/* Recent Trades */}
      {trades && trades.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Trades</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-dashboard-text-muted text-sm border-b border-dashboard-border">
                  <th className="pb-3 font-medium">Time</th>
                  <th className="pb-3 font-medium">Symbol</th>
                  <th className="pb-3 font-medium">Side</th>
                  <th className="pb-3 font-medium">Size</th>
                  <th className="pb-3 font-medium">Price</th>
                  <th className="pb-3 font-medium text-right">P&L</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {trades.slice(0, 5).map((trade) => (
                  <tr key={trade.id} className="border-b border-dashboard-border/50 last:border-0">
                    <td className="py-3 text-dashboard-text-muted">
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 font-medium">{trade.symbol}</td>
                    <td className="py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        trade.side === 'buy' 
                          ? 'bg-dashboard-accent/10 text-dashboard-accent' 
                          : 'bg-dashboard-danger/10 text-dashboard-danger'
                      }`}>
                        {trade.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3">${trade.size_usd.toFixed(2)}</td>
                    <td className="py-3">${trade.entry_price.toFixed(4)}</td>
                    <td className="py-3 text-right">
                      {trade.pnl !== undefined ? (
                        <span className={trade.pnl >= 0 ? 'text-dashboard-accent' : 'text-dashboard-danger'}>
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-dashboard-text-muted">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard

import React from 'react'
import { useTrades } from '@/hooks/useApi'
import { Trade } from '@/types'
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Filter,
  ArrowUpDown,
  Search
} from 'lucide-react'

const ITEMS_PER_PAGE = 20

export const TradesPanel: React.FC = () => {
  const { data: trades, isLoading } = useTrades(100)
  const [search, setSearch] = React.useState('')
  const [filter, setFilter] = React.useState<'all' | 'open' | 'closed'>('all')
  const [sortBy, setSortBy] = React.useState<'time' | 'pnl'>('time')
  const [page, setPage] = React.useState(1)
  
  const filteredTrades = React.useMemo(() => {
    if (!trades) return []
    
    return trades
      .filter((trade: Trade) => {
        if (search && !trade.symbol.toLowerCase().includes(search.toLowerCase())) {
          return false
        }
        if (filter !== 'all' && trade.status !== filter) {
          return false
        }
        return true
      })
      .sort((a: Trade, b: Trade) => {
        if (sortBy === 'time') {
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        }
        return (b.pnl || 0) - (a.pnl || 0)
      })
  }, [trades, search, filter, sortBy])
  
  const paginatedTrades = filteredTrades.slice(
    (page - 1) * ITEMS_PER_PAGE,
    page * ITEMS_PER_PAGE
  )
  
  const totalPages = Math.ceil(filteredTrades.length / ITEMS_PER_PAGE)
  
  const stats = React.useMemo(() => {
    if (!trades) return null
    
    const closed = trades.filter((t: Trade) => t.status === 'closed')
    const totalPnl = closed.reduce((sum: number, t: Trade) => sum + (t.pnl || 0), 0)
    const winCount = closed.filter((t: Trade) => (t.pnl || 0) > 0).length
    
    return {
      total: trades.length,
      closed: closed.length,
      open: trades.filter((t: Trade) => t.status === 'open').length,
      totalPnl,
      winRate: closed.length > 0 ? (winCount / closed.length) * 100 : 0,
    }
  }, [trades])

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-dashboard-accent"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="card">
            <p className="text-sm text-dashboard-text-muted">Total Trades</p>
            <p className="text-2xl font-bold text-white">{stats.total}</p>
          </div>
          <div className="card">
            <p className="text-sm text-dashboard-text-muted">Open Positions</p>
            <p className="text-2xl font-bold text-dashboard-accent">{stats.open}</p>
          </div>
          <div className="card">
            <p className="text-sm text-dashboard-text-muted">Win Rate</p>
            <p className="text-2xl font-bold text-white">{stats.winRate.toFixed(1)}%</p>
          </div>
          <div className="card">
            <p className="text-sm text-dashboard-text-muted">Total P&L</p>
            <p className={`text-2xl font-bold ${stats.totalPnl >= 0 ? 'text-dashboard-accent' : 'text-dashboard-danger'}`}>
              {stats.totalPnl >= 0 ? '+' : ''}${stats.totalPnl.toFixed(2)}
            </p>
          </div>
        </div>
      )}
      
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dashboard-text-muted" />
          <input
            type="text"
            placeholder="Search symbol..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white placeholder-dashboard-text-muted focus:outline-none focus:border-dashboard-accent"
          />
        </div>
        
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="px-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white focus:outline-none focus:border-dashboard-accent"
          >
            <option value="all">All Status</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
          
          <button
            onClick={() => setSortBy(sortBy === 'time' ? 'pnl' : 'time')}
            className="flex items-center gap-2 px-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white hover:border-dashboard-accent transition-colors"
          >
            <ArrowUpDown className="w-4 h-4" />
            Sort by {sortBy === 'time' ? 'P&L' : 'Time'}
          </button>
        </div>
      </div>
      
      {/* Trades Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-dashboard-text-muted text-sm border-b border-dashboard-border bg-dashboard-border/20">
                <th className="py-3 px-4 font-medium">Time</th>
                <th className="py-3 px-4 font-medium">Symbol</th>
                <th className="py-3 px-4 font-medium">Side</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium text-right">Size (USD)</th>
                <th className="py-3 px-4 font-medium text-right">Entry Price</th>
                <th className="py-3 px-4 font-medium text-right">Exit Price</th>
                <th className="py-3 px-4 font-medium text-right">P&L</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {paginatedTrades.map((trade: Trade) => (
                <tr 
                  key={trade.id} 
                  className="border-b border-dashboard-border/30 hover:bg-dashboard-border/10 transition-colors"
                >
                  <td className="py-3 px-4 text-dashboard-text-muted">
                    <div className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5" />
                      {new Date(trade.timestamp).toLocaleString()}
                    </div>
                  </td>
                  <td className="py-3 px-4 font-semibold">{trade.symbol}</td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                      trade.side === 'buy' 
                        ? 'bg-dashboard-accent/10 text-dashboard-accent' 
                        : 'bg-dashboard-danger/10 text-dashboard-danger'
                    }`}>
                      {trade.side === 'buy' ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {trade.side.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      trade.status === 'open'
                        ? 'bg-dashboard-info/10 text-dashboard-info'
                        : 'bg-dashboard-text-muted/10 text-dashboard-text-muted'
                    }`}>
                      {trade.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right font-mono">
                    ${trade.size_usd.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono">
                    ${trade.entry_price.toFixed(4)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono">
                    {trade.exit_price ? `$${trade.exit_price.toFixed(4)}` : '-'}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-medium">
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
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-dashboard-border">
            <p className="text-sm text-dashboard-text-muted">
              Showing {((page - 1) * ITEMS_PER_PAGE) + 1} to {Math.min(page * ITEMS_PER_PAGE, filteredTrades.length)} of {filteredTrades.length} trades
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-dashboard-border rounded text-sm disabled:opacity-50 hover:bg-dashboard-accent/20 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 bg-dashboard-border rounded text-sm disabled:opacity-50 hover:bg-dashboard-accent/20 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default TradesPanel

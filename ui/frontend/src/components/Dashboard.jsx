import { useState, useEffect } from 'react'

function Dashboard({ status }) {
  if (!status) return null

  const { bot, performance } = status

  const stats = [
    {
      label: 'Daily P&L',
      value: `$${performance.daily_pnl.toFixed(2)}`,
      color: performance.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600',
      bg: performance.daily_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'
    },
    {
      label: 'Weekly P&L',
      value: `$${performance.weekly_pnl.toFixed(2)}`,
      color: performance.weekly_pnl >= 0 ? 'text-green-600' : 'text-red-600',
      bg: performance.weekly_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'
    },
    {
      label: 'All-Time P&L',
      value: `$${performance.all_time_pnl.toFixed(2)}`,
      color: performance.all_time_pnl >= 0 ? 'text-green-600' : 'text-red-600',
      bg: performance.all_time_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'
    },
    {
      label: 'Win Rate',
      value: `${performance.win_rate.toFixed(1)}%`,
      color: performance.win_rate >= 50 ? 'text-green-600' : 'text-orange-600',
      bg: performance.win_rate >= 50 ? 'bg-green-50' : 'bg-orange-50'
    }
  ]

  const systemStats = [
    { label: 'Total Trades', value: performance.total_trades },
    { label: 'Open Positions', value: performance.open_positions },
    { label: 'Winning Trades', value: performance.winning_trades },
    { label: 'Losing Trades', value: performance.losing_trades }
  ]

  return (
    <div className="space-y-6">
      {/* P&L Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => (
          <div key={idx} className={`${stat.bg} rounded-lg p-6 border border-gray-200`}>
            <p className="text-sm text-gray-600 mb-2">{stat.label}</p>
            <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* System Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Trading Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {systemStats.map((stat, idx) => (
            <div key={idx} className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-600">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bot Status Details */}
      {bot.running && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">System Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Process ID</p>
              <p className="text-lg font-medium">{bot.pid}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">CPU Usage</p>
              <p className="text-lg font-medium">{bot.cpu_percent?.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Memory Usage</p>
              <p className="text-lg font-medium">{bot.memory_mb?.toFixed(1)} MB</p>
            </div>
          </div>
        </div>
      )}

      {/* Status Message */}
      {!bot.running && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center">
            <span className="text-2xl mr-3">⚠️</span>
            <div>
              <h3 className="text-lg font-semibold text-yellow-900">Bot is not running</h3>
              <p className="text-yellow-700 mt-1">
                Click the "Start Bot" button in the header to begin monitoring for arbitrage opportunities.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard

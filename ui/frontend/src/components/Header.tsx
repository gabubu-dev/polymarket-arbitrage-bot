import React from 'react'
import { useDashboardData, useBotControl } from '@/hooks/useApi'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useDashboardStore } from '@/context/DashboardStore'
import { 
  Play, 
  Square, 
  RotateCw, 
  RefreshCw,
  Activity,
  Cpu,
  Clock,
  Wifi,
  WifiOff
} from 'lucide-react'

const formatUptime = (seconds: number | null): string => {
  if (seconds === null) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

export const Header: React.FC = () => {
  const { data: dashboardData, refetch, isFetching } = useDashboardData()
  const { start, stop, restart } = useBotControl()
  const { isWebSocketConnected } = useDashboardStore()
  
  const botStatus = dashboardData?.bot
  const isRunning = botStatus?.running ?? false
  
  const handleStart = () => {
    if (window.confirm('Start the trading bot?')) {
      start.mutate()
    }
  }
  
  const handleStop = () => {
    if (window.confirm('Are you sure you want to stop the bot?')) {
      stop.mutate()
    }
  }
  
  const handleRestart = () => {
    if (window.confirm('Are you sure you want to restart the bot?')) {
      restart.mutate()
    }
  }

  return (
    <header className="bg-dashboard-card border-b border-dashboard-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center py-4 gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="text-3xl">🤖</div>
            <div>
              <h1 className="text-xl font-bold text-white">
                Polymarket Trading Bot
              </h1>
              <div className="flex items-center gap-3 mt-1">
                {/* Status */}
                <div className="flex items-center gap-2">
                  <div className={`status-indicator ${isRunning ? 'status-running' : 'status-stopped'}`}></div>
                  <span className={`text-sm font-medium ${isRunning ? 'text-dashboard-accent' : 'text-dashboard-danger'}`}>
                    {isRunning ? 'Running' : 'Stopped'}
                  </span>
                </div>
                
                {/* WebSocket Status */}
                <div className="flex items-center gap-1 text-dashboard-text-muted">
                  {isWebSocketConnected ? (
                    <Wifi className="w-3.5 h-3.5 text-dashboard-accent" />
                  ) : (
                    <WifiOff className="w-3.5 h-3.5 text-dashboard-danger" />
                  )}
                  <span className="text-xs">{isWebSocketConnected ? 'Live' : 'Polling'}</span>
                </div>
                
                {/* Uptime */}
                {isRunning && botStatus?.uptime_seconds && (
                  <div className="flex items-center gap-1 text-dashboard-text-muted">
                    <Clock className="w-3.5 h-3.5" />
                    <span className="text-xs">{formatUptime(botStatus.uptime_seconds)}</span>
                  </div>
                )}
                
                {/* CPU & Memory */}
                {isRunning && (
                  <>
                    {botStatus?.cpu_percent !== null && (
                      <div className="flex items-center gap-1 text-dashboard-text-muted">
                        <Cpu className="w-3.5 h-3.5" />
                        <span className="text-xs">{botStatus.cpu_percent?.toFixed(1)}%</span>
                      </div>
                    )}
                    {botStatus?.memory_mb !== null && (
                      <div className="flex items-center gap-1 text-dashboard-text-muted">
                        <Activity className="w-3.5 h-3.5" />
                        <span className="text-xs">{(botStatus.memory_mb! / 1024).toFixed(1)} GB</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
          
          {/* Control Buttons */}
          <div className="flex items-center gap-2">
            {!isRunning ? (
              <button
                onClick={handleStart}
                disabled={start.isPending}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
              >
                {start.isPending ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Start Bot
              </button>
            ) : (
              <>
                <button
                  onClick={handleStop}
                  disabled={stop.isPending}
                  className="btn-danger flex items-center gap-2 disabled:opacity-50"
                >
                  {stop.isPending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                  Stop
                </button>
                <button
                  onClick={handleRestart}
                  disabled={restart.isPending}
                  className="btn-secondary flex items-center gap-2 disabled:opacity-50"
                >
                  {restart.isPending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <RotateCw className="w-4 h-4" />
                  )}
                  Restart
                </button>
              </>
            )}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header

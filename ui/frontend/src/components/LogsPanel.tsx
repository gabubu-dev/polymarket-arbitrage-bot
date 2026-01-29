import React from 'react'
import { useLogs } from '@/hooks/useApi'
import { 
  Terminal, 
  Download, 
  Trash2, 
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Info,
  Search
} from 'lucide-react'

const LOG_LEVELS = {
  ERROR: { color: 'text-dashboard-danger', icon: AlertCircle },
  WARN: { color: 'text-dashboard-warning', icon: AlertCircle },
  INFO: { color: 'text-dashboard-info', icon: Info },
  DEBUG: { color: 'text-dashboard-text-muted', icon: CheckCircle },
}

export const LogsPanel: React.FC = () => {
  const [lines, setLines] = React.useState(100)
  const [search, setSearch] = React.useState('')
  const [autoScroll, setAutoScroll] = React.useState(true)
  const logsEndRef = React.useRef<HTMLDivElement>(null)
  
  const { data: logs, isLoading, refetch } = useLogs(lines)
  
  // Auto scroll to bottom
  React.useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])
  
  const filteredLogs = React.useMemo(() => {
    if (!logs) return []
    if (!search) return logs
    return logs.filter(log => log.toLowerCase().includes(search.toLowerCase()))
  }, [logs, search])
  
  const getLogLevel = (log: string) => {
    if (log.includes('ERROR')) return LOG_LEVELS.ERROR
    if (log.includes('WARN')) return LOG_LEVELS.WARN
    if (log.includes('DEBUG')) return LOG_LEVELS.DEBUG
    return LOG_LEVELS.INFO
  }
  
  const handleDownload = () => {
    const blob = new Blob([logs?.join('\n') || ''], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bot-logs-${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  const handleClear = () => {
    if (window.confirm('Clear all logs? This cannot be undone.')) {
      // API call to clear logs would go here
    }
  }

  return (
    <div className="p-6 space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dashboard-text-muted" />
          <input
            type="text"
            placeholder="Filter logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white placeholder-dashboard-text-muted focus:outline-none focus:border-dashboard-accent"
          />
        </div>
        
        <div className="flex gap-2">
          <select
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
            className="px-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white focus:outline-none focus:border-dashboard-accent"
          >
            <option value={50}>Last 50 lines</option>
            <option value={100}>Last 100 lines</option>
            <option value={500}>Last 500 lines</option>
            <option value={1000}>Last 1000 lines</option>
          </select>
          
          <label className="flex items-center gap-2 px-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-dashboard-border bg-dashboard-bg text-dashboard-accent focus:ring-dashboard-accent"
            />
            <span className="text-sm">Auto-scroll</span>
          </label>
          
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white hover:border-dashboard-accent transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 bg-dashboard-card border border-dashboard-border rounded-lg text-white hover:border-dashboard-accent transition-colors"
          >
            <Download className="w-4 h-4" />
          </button>
          
          <button
            onClick={handleClear}
            className="flex items-center gap-2 px-4 py-2 bg-dashboard-danger/10 border border-dashboard-danger/30 rounded-lg text-dashboard-danger hover:bg-dashboard-danger/20 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Log Terminal */}
      <div className="card p-0 overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-2 bg-dashboard-border/20 border-b border-dashboard-border">
          <Terminal className="w-4 h-4 text-dashboard-accent" />
          <span className="text-sm font-medium">Bot Logs</span>
          <span className="text-xs text-dashboard-text-muted ml-auto">
            {filteredLogs.length} lines
          </span>
        </div>
        
        <div className="h-[600px] overflow-y-auto p-4 font-mono text-sm">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-dashboard-text-muted">
              <RefreshCw className="w-6 h-6 animate-spin mr-2" />
              Loading logs...
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-dashboard-text-muted">
              No logs found
            </div>
          ) : (
            <div className="space-y-1">
              {filteredLogs.map((log, index) => {
                const level = getLogLevel(log)
                const Icon = level.icon
                
                return (
                  <div 
                    key={index} 
                    className="flex items-start gap-2 py-0.5 hover:bg-dashboard-border/10 rounded px-1"
                  >
                    <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${level.color}`} />
                    <span className="text-dashboard-text-muted break-all">{log}</span>
                  </div>
                )
              })}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default LogsPanel

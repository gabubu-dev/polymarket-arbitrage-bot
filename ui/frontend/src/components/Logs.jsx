import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

function Logs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [numLines, setNumLines] = useState(100)
  const logsEndRef = useRef(null)
  const logsContainerRef = useRef(null)

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 2000) // Refresh every 2 seconds
    return () => clearInterval(interval)
  }, [numLines])

  useEffect(() => {
    if (autoScroll) {
      // Delay scroll to ensure DOM has updated
      setTimeout(scrollToBottom, 100)
    }
  }, [logs, autoScroll])

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`/api/logs?lines=${numLines}`)
      // Handle both old format (array of strings) and new format (array of objects)
      const rawLogs = response.data.logs || []
      setLogs(rawLogs)
      setError(null)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleClearLogs = async () => {
    if (!confirm('Are you sure you want to clear all logs? This cannot be undone.')) return
    
    try {
      await axios.delete('/api/logs')
      setLogs([])
      alert('Logs cleared successfully')
    } catch (err) {
      alert(`Failed to clear logs: ${err.response?.data?.detail || err.message}`)
    }
  }

  const scrollToBottom = () => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }

  // Detect if user manually scrolled up
  const handleScroll = () => {
    if (logsContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
      setAutoScroll(isAtBottom)
    }
  }

  const getLevelColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'ERROR': return 'text-red-500'
      case 'WARNING': return 'text-yellow-500'
      case 'INFO': return 'text-blue-400'
      case 'DEBUG': return 'text-gray-400'
      case 'SUCCESS': return 'text-green-500'
      default: return 'text-gray-300'
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Controls */}
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <h2 className="text-xl font-semibold">Bot Logs</h2>
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Lines:</label>
            <select
              value={numLines}
              onChange={(e) => setNumLines(parseInt(e.target.value))}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="500">500</option>
            </select>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 text-sm text-gray-700">Auto-scroll</label>
          </div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={fetchLogs}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
          >
            🔄 Refresh
          </button>
          <button
            onClick={handleClearLogs}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm"
          >
            🗑️ Clear Logs
          </button>
        </div>
      </div>

      {/* Logs Display */}
      <div className="p-4">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Error loading logs: {error}</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No logs available
          </div>
        ) : (
          <div 
            ref={logsContainerRef}
            onScroll={handleScroll}
            className="bg-gray-900 rounded-lg p-4 overflow-y-auto font-mono text-xs leading-relaxed"
            style={{ 
              height: '65vh',
              maxHeight: '65vh',
              minHeight: '400px'
            }}
          >
            {logs.map((log, idx) => {
              // Handle both string format (old) and object format (new)
              if (typeof log === 'string') {
                return (
                  <div key={idx} className="text-gray-300 mb-1">
                    {log}
                  </div>
                )
              }
              
              // Structured log format
              return (
                <div key={idx} className="mb-1 hover:bg-gray-800 px-2 py-1 rounded transition-colors">
                  {log.timestamp && (
                    <span className="text-gray-500 mr-2">
                      {log.timestamp}
                    </span>
                  )}
                  {log.level && (
                    <span className={`${getLevelColor(log.level)} font-semibold mr-2`}>
                      [{log.level}]
                    </span>
                  )}
                  {log.logger && (
                    <span className="text-purple-400 mr-2">
                      {log.logger}
                    </span>
                  )}
                  <span className="text-gray-200">
                    {log.message}
                  </span>
                </div>
              )
            })}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* Stats */}
      {logs.length > 0 && (
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
          <p className="text-sm text-gray-600">
            Showing {logs.length} log lines • Last updated: {new Date().toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  )
}

export default Logs

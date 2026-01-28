import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

function Logs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [numLines, setNumLines] = useState(100)
  const logsEndRef = useRef(null)

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 5000)
    return () => clearInterval(interval)
  }, [numLines])

  useEffect(() => {
    if (autoScroll) {
      scrollToBottom()
    }
  }, [logs, autoScroll])

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`/api/logs?lines=${numLines}`)
      setLogs(response.data.logs)
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
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const getLogLineClass = (line) => {
    if (line.includes('ERROR') || line.includes('error')) return 'text-red-600'
    if (line.includes('WARNING') || line.includes('warning')) return 'text-yellow-600'
    if (line.includes('INFO') || line.includes('info')) return 'text-blue-600'
    if (line.includes('SUCCESS') || line.includes('success')) return 'text-green-600'
    return 'text-gray-700'
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
          <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-[600px] font-mono text-sm">
            {logs.map((line, idx) => (
              <div key={idx} className={`${getLogLineClass(line)} mb-1`}>
                {line}
              </div>
            ))}
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

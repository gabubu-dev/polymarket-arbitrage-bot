import { useState, useEffect } from 'react'
import axios from 'axios'
import Dashboard from './components/Dashboard'
import Configuration from './components/Configuration'
import Trades from './components/Trades'
import Logs from './components/Logs'

const API_BASE = '/api'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStatus()
    // Refresh every 1 second for live updates
    const interval = setInterval(fetchStatus, 1000)
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const [statusResponse, paperStatsResponse] = await Promise.all([
        axios.get(`${API_BASE}/status`),
        axios.get(`${API_BASE}/paper-stats`)
      ])
      
      // Merge paper trading stats with regular status
      setStatus({
        ...statusResponse.data,
        paperTrading: paperStatsResponse.data
      })
      setError(null)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleStart = async () => {
    try {
      await axios.post(`${API_BASE}/control/start`)
      setTimeout(fetchStatus, 1000)
    } catch (err) {
      alert(`Failed to start bot: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleStop = async () => {
    if (!confirm('Are you sure you want to stop the bot?')) return
    try {
      await axios.post(`${API_BASE}/control/stop`)
      setTimeout(fetchStatus, 1000)
    } catch (err) {
      alert(`Failed to stop bot: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleRestart = async () => {
    if (!confirm('Are you sure you want to restart the bot?')) return
    try {
      await axios.post(`${API_BASE}/control/restart`)
      setTimeout(fetchStatus, 2000)
    } catch (err) {
      alert(`Failed to restart bot: ${err.response?.data?.detail || err.message}`)
    }
  }

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'config', label: 'Configuration', icon: '⚙️' },
    { id: 'trades', label: 'Trades', icon: '💰' },
    { id: 'logs', label: 'Logs', icon: '📝' }
  ]

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 md:py-4">
          <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-3 md:gap-0">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl md:text-3xl font-bold text-gray-900 truncate">
                Polymarket Arbitrage Bot
              </h1>
              {status && (
                <div className="flex items-center mt-1 md:mt-2 space-x-3 md:space-x-4">
                  <span className={`flex items-center text-xs md:text-sm ${status.bot.running ? 'text-green-600' : 'text-red-600'}`}>
                    <span className={`w-2 h-2 rounded-full mr-1.5 md:mr-2 ${status.bot.running ? 'bg-green-600 animate-pulse' : 'bg-red-600'}`}></span>
                    {status.bot.running ? 'Running' : 'Stopped'}
                  </span>
                  {status.bot.running && status.bot.uptime_seconds && (
                    <span className="text-xs md:text-sm text-gray-600">
                      Uptime: {formatUptime(status.bot.uptime_seconds)}
                    </span>
                  )}
                </div>
              )}
            </div>
            
            {/* Control Buttons - Hidden: bots managed externally via command line */}
            <div className="flex space-x-2 w-full md:w-auto">
              <button
                onClick={fetchStatus}
                className="flex-1 md:flex-initial px-3 md:px-4 py-2.5 md:py-2 bg-blue-600 text-white text-sm md:text-base rounded-lg hover:bg-blue-700 active:bg-blue-800 transition touch-manipulation"
              >
                <span className="hidden sm:inline">🔄 Refresh</span>
                <span className="sm:hidden">🔄</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-3 md:mt-6">
        <div className="border-b border-gray-200 overflow-hidden">
          <nav className="-mb-px flex space-x-4 md:space-x-8 overflow-x-auto scrollbar-hide">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  whitespace-nowrap py-3 md:py-4 px-1 border-b-2 font-medium text-xs md:text-sm flex-shrink-0 touch-manipulation
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 active:text-gray-900'
                  }
                `}
              >
                <span className="mr-1">{tab.icon}</span>
                <span className="hidden xs:inline">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 md:py-8 pb-safe">
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-10 w-10 md:h-12 md:w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-sm md:text-base text-gray-600">Loading...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 md:p-4">
            <p className="text-sm md:text-base text-red-800">Error: {error}</p>
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && <Dashboard status={status} />}
            {activeTab === 'config' && <Configuration />}
            {activeTab === 'trades' && <Trades />}
            {activeTab === 'logs' && <Logs />}
          </>
        )}
      </main>
    </div>
  )
}

function formatUptime(seconds) {
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

export default App

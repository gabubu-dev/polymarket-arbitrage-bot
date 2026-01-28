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
    const interval = setInterval(fetchStatus, 5000) // Poll every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/status`)
      setStatus(response.data)
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
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Polymarket Arbitrage Bot
              </h1>
              {status && (
                <div className="flex items-center mt-2 space-x-4">
                  <span className={`flex items-center text-sm ${status.bot.running ? 'text-green-600' : 'text-red-600'}`}>
                    <span className={`w-2 h-2 rounded-full mr-2 ${status.bot.running ? 'bg-green-600' : 'bg-red-600'}`}></span>
                    {status.bot.running ? 'Running' : 'Stopped'}
                  </span>
                  {status.bot.running && status.bot.uptime_seconds && (
                    <span className="text-sm text-gray-600">
                      Uptime: {formatUptime(status.bot.uptime_seconds)}
                    </span>
                  )}
                </div>
              )}
            </div>
            
            {/* Control Buttons */}
            <div className="flex space-x-2">
              {!status?.bot.running ? (
                <button
                  onClick={handleStart}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                >
                  ▶️ Start Bot
                </button>
              ) : (
                <>
                  <button
                    onClick={handleStop}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                  >
                    ⏹️ Stop Bot
                  </button>
                  <button
                    onClick={handleRestart}
                    className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition"
                  >
                    🔄 Restart
                  </button>
                </>
              )}
              <button
                onClick={fetchStatus}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                🔄 Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Error: {error}</p>
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

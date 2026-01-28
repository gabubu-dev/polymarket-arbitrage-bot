import { useState, useEffect } from 'react'
import axios from 'axios'

function Configuration() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await axios.get('/api/config')
      setConfig(response.data)
      setLoading(false)
    } catch (err) {
      setMessage({ type: 'error', text: `Failed to load config: ${err.message}` })
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await axios.post('/api/config', config)
      setMessage({ type: 'success', text: 'Configuration saved successfully!' })
      setTimeout(() => setMessage(null), 3000)
    } catch (err) {
      setMessage({ type: 'error', text: `Failed to save: ${err.response?.data?.detail || err.message}` })
    }
    setSaving(false)
  }

  const updateConfig = (path, value) => {
    setConfig(prevConfig => {
      const newConfig = JSON.parse(JSON.stringify(prevConfig))
      const keys = path.split('.')
      let current = newConfig
      
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {}
        current = current[keys[i]]
      }
      
      current[keys[keys.length - 1]] = value
      return newConfig
    })
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Message Banner */}
      {message && (
        <div className={`rounded-lg p-4 ${message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {message.text}
        </div>
      )}

      {/* Polymarket API */}
      <section className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Polymarket API</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
            <input
              type="password"
              value={config.polymarket?.api_key || ''}
              onChange={(e) => updateConfig('polymarket.api_key', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter API key"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">API Secret</label>
            <input
              type="password"
              value={config.polymarket?.api_secret || ''}
              onChange={(e) => updateConfig('polymarket.api_secret', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter API secret"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Private Key</label>
            <input
              type="password"
              value={config.polymarket?.private_key || ''}
              onChange={(e) => updateConfig('polymarket.private_key', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter private key"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Chain ID</label>
            <input
              type="number"
              value={config.polymarket?.chain_id || 137}
              onChange={(e) => updateConfig('polymarket.chain_id', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </section>

      {/* Exchange APIs */}
      <section className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Exchange APIs</h2>
        
        {/* Binance */}
        <div className="mb-6">
          <h3 className="text-lg font-medium mb-3">Binance</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
              <input
                type="password"
                value={config.exchanges?.binance?.api_key || ''}
                onChange={(e) => updateConfig('exchanges.binance.api_key', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter Binance API key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Secret</label>
              <input
                type="password"
                value={config.exchanges?.binance?.api_secret || ''}
                onChange={(e) => updateConfig('exchanges.binance.api_secret', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter Binance API secret"
              />
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={config.exchanges?.binance?.testnet || false}
                onChange={(e) => updateConfig('exchanges.binance.testnet', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label className="ml-2 text-sm text-gray-700">Use Testnet</label>
            </div>
          </div>
        </div>

        {/* Coinbase */}
        <div>
          <h3 className="text-lg font-medium mb-3">Coinbase</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
              <input
                type="password"
                value={config.exchanges?.coinbase?.api_key || ''}
                onChange={(e) => updateConfig('exchanges.coinbase.api_key', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter Coinbase API key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Secret</label>
              <input
                type="password"
                value={config.exchanges?.coinbase?.api_secret || ''}
                onChange={(e) => updateConfig('exchanges.coinbase.api_secret', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter Coinbase API secret"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Trading Parameters */}
      <section className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Trading Parameters</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Divergence Threshold (%)
            </label>
            <input
              type="number"
              step="0.01"
              value={(config.trading?.divergence_threshold || 0.05) * 100}
              onChange={(e) => updateConfig('trading.divergence_threshold', parseFloat(e.target.value) / 100)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Min Profit Threshold (%)
            </label>
            <input
              type="number"
              step="0.01"
              value={(config.trading?.min_profit_threshold || 0.02) * 100}
              onChange={(e) => updateConfig('trading.min_profit_threshold', parseFloat(e.target.value) / 100)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Position Size (USD)
            </label>
            <input
              type="number"
              value={config.trading?.position_size_usd || 100}
              onChange={(e) => updateConfig('trading.position_size_usd', parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Positions
            </label>
            <input
              type="number"
              value={config.trading?.max_positions || 5}
              onChange={(e) => updateConfig('trading.max_positions', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Position Size (USD)
            </label>
            <input
              type="number"
              value={config.trading?.max_position_size_usd || 500}
              onChange={(e) => updateConfig('trading.max_position_size_usd', parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </section>

      {/* Risk Management */}
      <section className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Risk Management</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Stop Loss (%)
            </label>
            <input
              type="number"
              step="0.01"
              value={(config.risk_management?.stop_loss_percentage || 0.15) * 100}
              onChange={(e) => updateConfig('risk_management.stop_loss_percentage', parseFloat(e.target.value) / 100)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Take Profit (%)
            </label>
            <input
              type="number"
              step="0.01"
              value={(config.risk_management?.take_profit_percentage || 0.90) * 100}
              onChange={(e) => updateConfig('risk_management.take_profit_percentage', parseFloat(e.target.value) / 100)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Daily Loss (USD)
            </label>
            <input
              type="number"
              value={config.risk_management?.max_daily_loss_usd || 1000}
              onChange={(e) => updateConfig('risk_management.max_daily_loss_usd', parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Emergency Shutdown Loss (USD)
            </label>
            <input
              type="number"
              value={config.risk_management?.emergency_shutdown_loss_usd || 5000}
              onChange={(e) => updateConfig('risk_management.emergency_shutdown_loss_usd', parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      </section>

      {/* Notifications */}
      <section className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Notifications</h2>
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={config.notifications?.enabled || false}
              onChange={(e) => updateConfig('notifications.enabled', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 text-sm text-gray-700">Enable Notifications</label>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Webhook URL
            </label>
            <input
              type="password"
              value={config.notifications?.webhook_url || ''}
              onChange={(e) => updateConfig('notifications.webhook_url', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter webhook URL (Discord, Slack, etc.)"
            />
          </div>
        </div>
      </section>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  )
}

export default Configuration

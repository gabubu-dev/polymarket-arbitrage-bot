import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DetailedStats from './DetailedStats';
import LiveTradeFeed from './LiveTradeFeed';
import OpenPositions from './OpenPositions';

export default function Dashboard({ status }) {
  const [combinedStats, setCombinedStats] = useState(null);
  const [botsInfo, setBotsInfo] = useState(null);
  
  useEffect(() => {
    fetchCombinedData();
    // Refresh every 1 second for live updates
    const interval = setInterval(fetchCombinedData, 1000);
    return () => clearInterval(interval);
  }, []);
  
  const fetchCombinedData = async () => {
    try {
      const [statsRes, botsRes] = await Promise.all([
        axios.get('/api/combined-stats'),
        axios.get('/api/bots')
      ]);
      setCombinedStats(statsRes.data);
      setBotsInfo(botsRes.data);
    } catch (err) {
      console.error('Failed to fetch combined data:', err);
    }
  };

  if (!status) return null;

  // Prepare stats for DetailedStats component
  const stats = {
    combined: {
      balance: combinedStats?.combined?.total_balance || 2000.00,
      equity: combinedStats?.combined?.total_equity || 2000.00,
      pnl: combinedStats?.combined?.total_pnl || 0.00,
      positions: combinedStats?.combined?.total_open_positions || 0,
      trades: combinedStats?.combined?.total_trades || 0,
      winRate: combinedStats?.combined?.combined_win_rate || 0,
      wins: (combinedStats?.primary?.winning_trades || 0) + (combinedStats?.secondary?.winning_trades || 0),
      losses: (combinedStats?.primary?.losing_trades || 0) + (combinedStats?.secondary?.losing_trades || 0)
    },
    primary: combinedStats?.primary ? {
      balance: combinedStats.primary.balance,
      pnl: combinedStats.primary.total_pnl,
      positions: combinedStats.primary.open_positions
    } : null,
    secondary: combinedStats?.secondary ? {
      balance: combinedStats.secondary.balance,
      pnl: combinedStats.secondary.total_pnl,
      positions: combinedStats.secondary.open_positions
    } : null
  };

  return (
    <div className="dashboard p-4 space-y-6">
      {/* Header */}
      <div className="header text-center md:text-left">
        <h1 className="text-3xl font-bold flex items-center justify-center md:justify-start gap-2">
          <span>🎮</span> Trading Dashboard
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Updates every second • Simple view for beginners
        </p>
      </div>

      {/* Welcome Message for Beginners */}
      <div className="bg-gradient-to-r from-blue-900 to-purple-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">👋</span>
          <div>
            <h3 className="font-semibold text-blue-300 mb-1">Welcome to Trading!</h3>
            <p className="text-sm text-blue-400">
              This dashboard shows how your automated trading bot is doing. 
              <span className="text-green-400"> Green means making money</span>, 
              <span className="text-red-400"> red means losing money</span>. 
              It's like betting on sports, but for financial markets!
            </p>
          </div>
        </div>
      </div>

      {/* Your Money Section */}
      <div>
        <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
          <span>💰</span> Your Money & Performance
        </h2>
        <DetailedStats stats={stats} />
      </div>

      {/* Two-column layout for desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Live Trade Feed */}
        <LiveTradeFeed />

        {/* Bot Status */}
        <div className="bot-status-panel">
          <div className="mb-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <span>🤖</span> Bot Status
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Your automated trading bots (they make trades for you)
            </p>
          </div>
          
          <div className="space-y-3">
            {botsInfo?.primary && (
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="font-semibold text-white">Bot #1: Primary</span>
                    <div className="text-xs text-gray-500">Main trading bot</div>
                  </div>
                  <span className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold ${
                    botsInfo.primary.status === 'running' 
                      ? 'bg-green-900 bg-opacity-30 text-green-400 border border-green-700' 
                      : 'bg-red-900 bg-opacity-30 text-red-400 border border-red-700'
                  }`}>
                    {botsInfo.primary.status === 'running' && <span className="animate-pulse">●</span>}
                    {botsInfo.primary.status === 'running' ? '✅ Running' : '⏸️ Stopped'}
                  </span>
                </div>
                {stats.primary && (
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="text-center p-2 bg-gray-800 rounded">
                      <div className="text-xs text-gray-500 mb-1">Money</div>
                      <div className="text-white font-semibold">${stats.primary.balance?.toFixed(2)}</div>
                    </div>
                    <div className="text-center p-2 bg-gray-800 rounded">
                      <div className="text-xs text-gray-500 mb-1">Active</div>
                      <div className="text-white font-semibold">{stats.primary.positions || 0}</div>
                    </div>
                    <div className="text-center p-2 bg-gray-800 rounded">
                      <div className="text-xs text-gray-500 mb-1">Profit/Loss</div>
                      <div className={`font-semibold ${stats.primary.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${Math.abs(stats.primary.pnl)?.toFixed(2)}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {botsInfo?.secondary && (
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="font-semibold text-white">Bot #2: Secondary</span>
                    <div className="text-xs text-gray-500">Backup trading bot</div>
                  </div>
                  <span className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold ${
                    botsInfo.secondary.status === 'running' 
                      ? 'bg-green-900 bg-opacity-30 text-green-400 border border-green-700' 
                      : 'bg-red-900 bg-opacity-30 text-red-400 border border-red-700'
                  }`}>
                    {botsInfo.secondary.status === 'running' && <span className="animate-pulse">●</span>}
                    {botsInfo.secondary.status === 'running' ? '✅ Running' : '⏸️ Stopped'}
                  </span>
                </div>
                {stats.secondary && (
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="text-center p-2 bg-gray-800 rounded">
                      <div className="text-xs text-gray-500 mb-1">Money</div>
                      <div className="text-white font-semibold">${stats.secondary.balance?.toFixed(2)}</div>
                    </div>
                    <div className="text-center p-2 bg-gray-800 rounded">
                      <div className="text-xs text-gray-500 mb-1">Active</div>
                      <div className="text-white font-semibold">{stats.secondary.positions || 0}</div>
                    </div>
                    <div className="text-center p-2 bg-gray-800 rounded">
                      <div className="text-xs text-gray-500 mb-1">Profit/Loss</div>
                      <div className={`font-semibold ${stats.secondary.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${Math.abs(stats.secondary.pnl)?.toFixed(2)}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Quick Explainer */}
            <div className="bg-purple-900 bg-opacity-20 border border-purple-700 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <span className="text-lg">💡</span>
                <div className="text-xs text-purple-300">
                  <div className="font-semibold mb-1">What are these bots?</div>
                  <div className="text-purple-400">
                    Think of them as your employees who trade for you automatically. 
                    They watch the markets 24/7 and make trades when they spot opportunities.
                  </div>
                </div>
              </div>
            </div>

            {/* System Info (if available) */}
            {status?.bot?.running && (
              <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
                <h4 className="font-semibold mb-2 text-sm text-gray-400">System Resources</h4>
                <div className="text-xs text-gray-500 space-y-1">
                  <div className="flex justify-between">
                    <span>Process ID:</span>
                    <span className="text-white">{status.bot.pid}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>CPU Usage:</span>
                    <span className="text-white">{status.bot.cpu_percent?.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Memory:</span>
                    <span className="text-white">{status.bot.memory_mb?.toFixed(1)} MB</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Open Positions Table */}
      <OpenPositions />

      {/* Warning if no bots running */}
      {!botsInfo?.primary?.status === 'running' && !botsInfo?.secondary?.status === 'running' && (
        <div className="bg-yellow-900 bg-opacity-20 border border-yellow-700 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <h3 className="text-base font-semibold text-yellow-400">Bots are sleeping 😴</h3>
              <p className="text-sm text-yellow-500 mt-1">
                Your trading bots aren't running. Click "Start Bot" in the top menu to wake them up and start trading!
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

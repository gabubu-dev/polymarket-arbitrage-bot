import React, { useState, useEffect, useRef } from 'react';

export default function LiveTradeFeed() {
  const [trades, setTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  const tradesFeedRef = useRef(null);

  const fetchData = async () => {
    try {
      // Fetch recent trades
      const tradesRes = await fetch('/api/paper-trades?limit=50');
      const tradesData = await tradesRes.json();
      setTrades(tradesData.trades || []);

      // Fetch positions
      const posRes = await fetch('/api/all-positions');
      const posData = await posRes.json();
      setPositions(posData.positions || []);
    } catch (error) {
      console.error('Failed to fetch trade data:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 1000); // 1 second refresh
    return () => clearInterval(interval);
  }, []);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false });
  };

  const getStatusColor = (status) => {
    return status === 'open' ? 'text-blue-400' : 'text-green-400';
  };

  const getStatusText = (status) => {
    return status === 'open' ? 'ACTIVE' : 'CLOSED';
  };

  const getDirectionEmoji = (direction) => {
    return direction === 'up' ? '📈' : '📉';
  };

  const getDirectionText = (direction) => {
    return direction === 'up' ? 'Betting UP' : 'Betting DOWN';
  };

  const getProfitText = (pnl) => {
    if (!pnl) return null;
    const emoji = pnl >= 0 ? '💰' : '💸';
    const action = pnl >= 0 ? 'Won' : 'Lost';
    return `${emoji} ${action} $${Math.abs(pnl).toFixed(2)}`;
  };

  return (
    <div className="live-trade-feed">
      <div className="mb-3">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="animate-pulse text-green-400">●</span>
          Live Trading Activity
        </h3>
        <p className="text-xs text-gray-500 mt-1">
          Real-time updates showing every trade as it happens
        </p>
      </div>
      
      <div 
        ref={tradesFeedRef}
        className="feed-container bg-black rounded-lg p-3 overflow-y-auto border border-gray-700"
        style={{ height: '400px' }}
      >
        {trades.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">🎲</div>
            <div>Waiting for trades...</div>
            <div className="text-xs mt-2">Your trades will appear here</div>
          </div>
        ) : (
          trades.map((trade, idx) => (
            <div 
              key={idx}
              className="trade-item mb-2 p-3 bg-gray-900 rounded border-l-4 border-blue-500 hover:bg-gray-800 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  {/* Direction and Market */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">{getDirectionEmoji(trade.direction || trade.outcome)}</span>
                    <span className="font-semibold text-white text-sm">
                      {getDirectionText(trade.direction || trade.outcome)}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded ${getStatusColor(trade.status || 'closed')} bg-opacity-20`}>
                      {getStatusText(trade.status || 'closed')}
                    </span>
                  </div>
                  
                  {/* Market Info */}
                  <div className="text-xs text-gray-400 mb-2">
                    Market: {trade.market_id}
                  </div>
                  
                  {/* Trade Details */}
                  <div className="text-xs text-gray-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Bought at:</span>
                      <span className="text-white">${trade.price?.toFixed(3)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Amount:</span>
                      <span className="text-white">${trade.amount?.toFixed(2)}</span>
                    </div>
                    {trade.realized_pnl !== undefined && trade.realized_pnl !== null && (
                      <div className={`flex justify-between font-semibold ${trade.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        <span>Result:</span>
                        <span>{getProfitText(trade.realized_pnl)}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Time */}
                <div className="text-right text-xs text-gray-500 ml-2">
                  {formatTime(trade.timestamp)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Helper Text */}
      <div className="mt-2 text-xs text-gray-500 px-2">
        <span className="text-green-400">●</span> Green = Making money
        <span className="mx-2">•</span>
        <span className="text-red-400">●</span> Red = Losing money
        <span className="mx-2">•</span>
        <span className="text-blue-400">●</span> Blue = Active trade
      </div>
    </div>
  );
}

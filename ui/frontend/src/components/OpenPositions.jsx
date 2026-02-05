import React, { useState, useEffect } from 'react';
import Tooltip from './Tooltip';

export default function OpenPositions() {
  const [positions, setPositions] = useState([]);

  const fetchPositions = async () => {
    try {
      const response = await fetch('/api/all-positions');
      const data = await response.json();
      const openPos = (data.positions || []).filter(p => p.status === 'open');
      setPositions(openPos);
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 1000);
    return () => clearInterval(interval);
  }, []);

  const getDirectionDisplay = (direction) => {
    if (direction === 'up') {
      return {
        emoji: '📈',
        text: 'UP',
        color: 'text-green-400',
        description: 'Betting market goes up'
      };
    } else {
      return {
        emoji: '📉',
        text: 'DOWN',
        color: 'text-red-400',
        description: 'Betting market goes down'
      };
    }
  };

  return (
    <div className="open-positions mt-4">
      <div className="mb-3">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span>🎯</span> Active Trades ({positions.length})
        </h3>
        <p className="text-xs text-gray-500 mt-1">
          These trades are still running. You'll make or lose money when they close.
        </p>
      </div>
      
      {positions.length === 0 ? (
        <div className="bg-gray-900 rounded-lg p-6 text-center text-gray-500">
          <div className="text-4xl mb-2">💤</div>
          <div className="font-semibold mb-1">No active trades</div>
          <div className="text-xs">When the bot makes a trade, it'll show up here</div>
        </div>
      ) : (
        <div className="overflow-x-auto bg-gray-900 rounded-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700">
                <th className="p-3 text-left">
                  <Tooltip text="Which market you're trading">
                    Market
                  </Tooltip>
                </th>
                <th className="p-3 text-left">
                  <Tooltip text="Whether you're betting the market goes UP or DOWN">
                    Prediction
                  </Tooltip>
                </th>
                <th className="p-3 text-right">
                  <Tooltip text="The price you bought at">
                    Bought At
                  </Tooltip>
                </th>
                <th className="p-3 text-right">
                  <Tooltip text="How much money you put into this trade">
                    Amount
                  </Tooltip>
                </th>
                <th className="p-3 text-right">
                  <Tooltip text="How much you're winning or losing right now (changes until trade closes)">
                    Current Profit/Loss
                  </Tooltip>
                </th>
                <th className="p-3 text-left">
                  <Tooltip text="When you started this trade">
                    Started
                  </Tooltip>
                </th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, idx) => {
                const direction = getDirectionDisplay(pos.direction);
                return (
                  <tr key={idx} className="border-t border-gray-800 hover:bg-gray-800 transition-colors">
                    <td className="p-3 text-white font-medium">
                      {pos.symbol || pos.market_id}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span>{direction.emoji}</span>
                        <div>
                          <div className={`${direction.color} font-semibold`}>
                            {direction.text}
                          </div>
                          <div className="text-xs text-gray-500">
                            {direction.description}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-right text-white">
                      ${pos.entry_price?.toFixed(3)}
                    </td>
                    <td className="p-3 text-right text-white">
                      ${pos.size_usd?.toFixed(2)}
                    </td>
                    <td className="p-3 text-right">
                      {pos.unrealized_pnl ? (
                        <div className="flex flex-col items-end">
                          <span className={`font-bold ${pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {pos.unrealized_pnl >= 0 ? '💰' : '💸'} ${Math.abs(pos.unrealized_pnl).toFixed(2)}
                          </span>
                          <span className="text-xs text-gray-500">
                            {pos.unrealized_pnl >= 0 ? 'Winning' : 'Losing'}
                          </span>
                        </div>
                      ) : (
                        <span className="text-gray-500">--</span>
                      )}
                    </td>
                    <td className="p-3 text-gray-400 text-xs">
                      {pos.entry_time ? new Date(pos.entry_time).toLocaleTimeString() : '--'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      
      {/* Helper Section */}
      {positions.length > 0 && (
        <div className="mt-3 bg-blue-900 bg-opacity-20 border border-blue-700 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <span className="text-lg">💡</span>
            <div className="text-xs text-blue-300">
              <div className="font-semibold mb-1">How it works:</div>
              <div className="space-y-1 text-blue-400">
                <div>• If you bet UP and the market goes up, you make money</div>
                <div>• If you bet DOWN and the market goes down, you make money</div>
                <div>• The "Current Profit/Loss" shows what you'd win/lose if you closed now</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

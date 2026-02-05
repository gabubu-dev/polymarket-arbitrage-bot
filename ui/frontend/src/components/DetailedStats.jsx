import React from 'react';
import Tooltip from './Tooltip';

export default function DetailedStats({ stats }) {
  const statItems = [
    { 
      label: 'Money Available', 
      tooltip: 'Cash you can use to make new trades',
      value: `$${stats?.combined?.balance?.toFixed(2) || '0.00'}`, 
      color: 'text-blue-400',
      emoji: '💵'
    },
    { 
      label: 'Total Worth', 
      tooltip: 'Your cash + value of all active trades',
      value: `$${stats?.combined?.equity?.toFixed(2) || '0.00'}`, 
      color: 'text-purple-400',
      emoji: '💰'
    },
    { 
      label: 'Total Profit/Loss', 
      tooltip: 'How much money you\'ve made or lost overall',
      value: `$${stats?.combined?.pnl?.toFixed(2) || '0.00'}`, 
      color: stats?.combined?.pnl >= 0 ? 'text-green-400' : 'text-red-400',
      emoji: stats?.combined?.pnl >= 0 ? '📈' : '📉'
    },
    { 
      label: 'Active Trades', 
      tooltip: 'Trades currently running (not closed yet)',
      value: stats?.combined?.positions || '0', 
      color: 'text-yellow-400',
      emoji: '🎯'
    },
    { 
      label: 'Trades Made', 
      tooltip: 'Total number of trades you\'ve made',
      value: stats?.combined?.trades || '0', 
      color: 'text-orange-400',
      emoji: '📊'
    },
    { 
      label: 'Success Rate', 
      tooltip: 'Percentage of trades that made money',
      value: `${stats?.combined?.winRate || '0'}%`, 
      color: 'text-green-400',
      emoji: '🎯'
    },
    { 
      label: 'Winning Trades', 
      tooltip: 'Trades that made you money',
      value: stats?.combined?.wins || '0', 
      color: 'text-green-400',
      emoji: '✅'
    },
    { 
      label: 'Losing Trades', 
      tooltip: 'Trades that lost money',
      value: stats?.combined?.losses || '0', 
      color: 'text-red-400',
      emoji: '❌'
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {statItems.map((item, idx) => (
        <div key={idx} className="stat-card bg-gray-900 rounded-lg p-3 border border-gray-700">
          <Tooltip text={item.tooltip}>
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-1 flex items-center gap-1">
              <span>{item.emoji}</span>
              <span>{item.label}</span>
            </div>
          </Tooltip>
          <div className={`text-xl font-bold ${item.color}`}>
            {item.value}
          </div>
        </div>
      ))}
    </div>
  );
}

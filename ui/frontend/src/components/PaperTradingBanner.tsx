import React from 'react'
import { useDashboardStore } from '@/context/DashboardStore'
import { Wallet, TrendingUp, TrendingDown } from 'lucide-react'

export const PaperTradingBanner: React.FC = () => {
  const { dashboardData, getPaperTradingPnl, getPaperTradingPnlPercent } = useDashboardStore()
  
  const paperTrading = dashboardData?.paper_trading
  
  if (!paperTrading?.enabled) {
    return null
  }
  
  const pnl = getPaperTradingPnl()
  const pnlPercent = getPaperTradingPnlPercent()
  const isPositive = pnl >= 0
  
  return (
    <div className="relative overflow-hidden">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-r from-banner-purple to-[#764ba2]"></div>
      
      {/* Animated shimmer effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full animate-[shimmer_3s_infinite]"></div>
      
      {/* Content */}
      <div className="relative px-6 py-5 text-center">
        <div className="flex items-center justify-center gap-2 mb-1">
          <span className="text-2xl">📝</span>
          <h2 className="text-xl font-bold text-white tracking-wide">
            PAPER TRADING MODE
          </h2>
        </div>
        
        <p className="text-white/80 text-sm mb-3">
          All trades are SIMULATED — No real money at risk
        </p>
        
        <div className="flex items-center justify-center gap-4">
          <div className="flex items-center gap-2 bg-black/20 rounded-full px-4 py-2">
            <Wallet className="w-5 h-5 text-white/80" />
            <span className="text-2xl font-bold text-white">
              ${paperTrading.virtual_balance.toLocaleString('en-US', { 
                minimumFractionDigits: 2, 
                maximumFractionDigits: 2 
              })}
            </span>
          </div>
          
          <div className={`flex items-center gap-1 text-sm font-semibold ${
            isPositive ? 'text-dashboard-accent' : 'text-dashboard-danger'
          }`}>
            {isPositive ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>
              {isPositive ? '+' : ''}${pnl.toFixed(2)} ({isPositive ? '+' : ''}{pnlPercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>
      
      {/* Bottom border glow */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-banner-pink to-transparent"></div>
    </div>
  )
}

export default PaperTradingBanner

import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  icon?: React.ReactNode
  loading?: boolean
  className?: string
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  icon,
  loading = false,
  className = '',
}) => {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-dashboard-accent" />
      case 'down':
        return <TrendingDown className="w-4 h-4 text-dashboard-danger" />
      default:
        return <Minus className="w-4 h-4 text-dashboard-text-muted" />
    }
  }
  
  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-dashboard-accent'
      case 'down':
        return 'text-dashboard-danger'
      default:
        return 'text-dashboard-text-muted'
    }
  }

  if (loading) {
    return (
      <div className={`card card-hover animate-pulse ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="h-4 bg-dashboard-border rounded w-24"></div>
          {icon && <div className="h-5 w-5 bg-dashboard-border rounded"></div>}
        </div>
        <div className="h-8 bg-dashboard-border rounded w-20"></div>
      </div>
    )
  }

  return (
    <div className={`card card-hover ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-dashboard-text-muted uppercase tracking-wider">
          {title}
        </h3>
        {icon && <div className="text-dashboard-text-muted">{icon}</div>}
      </div>
      
      <div className="flex items-baseline gap-2">
        <span className="stat-value">{value}</span>
        {trend && (
          <div className={`flex items-center gap-1 text-sm font-medium ${getTrendColor()}`}>
            {getTrendIcon()}
            {trendValue && <span>{trendValue}</span>}
          </div>
        )}
      </div>
      
      {subtitle && (
        <p className="text-sm text-dashboard-text-muted mt-1">{subtitle}</p>
      )}
    </div>
  )
}

export default StatCard

import React from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Loader2 } from 'lucide-react'

type ChartType = 'line' | 'area' | 'bar' | 'pie'

interface ChartPanelProps {
  title: string
  type: ChartType
  data: unknown[]
  dataKey: string
  xAxisKey?: string
  height?: number
  loading?: boolean
  colors?: string[]
  multiSeries?: { key: string; name: string; color: string }[]
}

const DEFAULT_COLORS = ['#00ff88', '#667eea', '#f093fb', '#ffd166', '#ff6b6b', '#118ab2']

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{value: number; name: string; color: string}>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-dashboard-card border border-dashboard-border rounded-lg p-3 shadow-lg">
        <p className="text-dashboard-text-muted text-sm mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm font-medium" style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(4) : entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export const ChartPanel: React.FC<ChartPanelProps> = ({
  title,
  type,
  data,
  dataKey,
  xAxisKey = 'name',
  height = 300,
  loading = false,
  colors = DEFAULT_COLORS,
  multiSeries,
}) => {
  if (loading) {
    return (
      <div className="chart-container">
        <h3 className="text-lg font-semibold text-white mb-4 pb-3 border-b border-dashboard-border">
          {title}
        </h3>
        <div className="flex items-center justify-center" style={{ height }}>
          <Loader2 className="w-8 h-8 animate-spin text-dashboard-accent" />
        </div>
      </div>
    )
  }

  const renderChart = () => {
    switch (type) {
      case 'area':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors[0]} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={colors[0]} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" opacity={0.5} />
              <XAxis 
                dataKey={xAxisKey} 
                stroke="#888" 
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#0f3460' }}
              />
              <YAxis 
                stroke="#888" 
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#0f3460' }}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey={dataKey} 
                stroke={colors[0]} 
                strokeWidth={2}
                fill="url(#colorGradient)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" opacity={0.5} />
              <XAxis 
                dataKey={xAxisKey} 
                stroke="#888" 
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#0f3460' }}
              />
              <YAxis 
                stroke="#888" 
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#0f3460' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ paddingTop: '10px' }} />
              {multiSeries ? (
                multiSeries.map((series, index) => (
                  <Line
                    key={series.key}
                    type="monotone"
                    dataKey={series.key}
                    name={series.name}
                    stroke={series.color}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 0 }}
                  />
                ))
              ) : (
                <Line 
                  type="monotone" 
                  dataKey={dataKey} 
                  stroke={colors[0]} 
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 0 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f3460" opacity={0.5} />
              <XAxis 
                dataKey={xAxisKey} 
                stroke="#888" 
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#0f3460' }}
              />
              <YAxis 
                stroke="#888" 
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#0f3460' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={dataKey} radius={[4, 4, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={(entry as Record<string, number>)[dataKey] >= 0 ? colors[0] : colors[4]} 
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey={dataKey}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </ResponsiveContainer>
        )

      default:
        return null
    }
  }

  return (
    <div className="chart-container">
      <h3 className="text-lg font-semibold text-white mb-4 pb-3 border-b border-dashboard-border">
        {title}
      </h3>
      <div className="w-full">
        {renderChart()}
      </div>
    </div>
  )
}

export default ChartPanel

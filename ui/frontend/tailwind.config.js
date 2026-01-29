import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Custom dashboard colors
        dashboard: {
          bg: '#1a1a2e',
          card: '#16213e',
          border: '#0f3460',
          accent: '#00ff88',
          'accent-dim': 'rgba(0, 255, 136, 0.1)',
          danger: '#ff6b6b',
          warning: '#ffd166',
          info: '#118ab2',
          text: '#eee',
          'text-muted': '#888',
        },
        // Paper trading banner gradient colors
        banner: {
          purple: '#667eea',
          pink: '#f093fb',
        }
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-down': 'slide-down 0.3s ease-out',
        'fade-in': 'fade-in 0.2s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 10px #00ff88' },
          '50%': { boxShadow: '0 0 20px #00ff88, 0 0 30px #00ff88' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config

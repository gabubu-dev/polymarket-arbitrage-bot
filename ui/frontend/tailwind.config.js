/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      spacing: {
        'safe': 'env(safe-area-inset-bottom)',
        'safe-top': 'env(safe-area-inset-top)',
      },
      screens: {
        'xs': '475px',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      const newUtilities = {
        '.scrollbar-hide': {
          /* Firefox */
          'scrollbar-width': 'none',
          /* Safari and Chrome */
          '&::-webkit-scrollbar': {
            display: 'none'
          }
        },
        '.pb-safe': {
          'padding-bottom': 'env(safe-area-inset-bottom)'
        },
        '.pt-safe': {
          'padding-top': 'env(safe-area-inset-top)'
        },
        '.touch-manipulation': {
          'touch-action': 'manipulation'
        }
      }
      addUtilities(newUtilities)
    }
  ],
}

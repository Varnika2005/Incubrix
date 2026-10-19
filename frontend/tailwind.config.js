/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          violet: '#6654F0',
          indigo: '#4435C8',
          cyan: '#15B8C9',
          coral: '#FF8B70',
          mint: '#BDEFD8',
        },
        surface: {
          main: '#F7F6FC',
          card: '#FFFFFF',
          secondary: '#EFEDF8',
          border: '#E6E2F0',
        },
        ink: {
          main: '#191832',
          muted: '#66627B',
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(25, 24, 50, 0.05), 0 1px 2px -1px rgba(25, 24, 50, 0.03)',
        'card': '0 4px 20px -2px rgba(25, 24, 50, 0.06), 0 2px 6px -1px rgba(25, 24, 50, 0.04)',
        'glow': '0 8px 30px rgba(102, 84, 240, 0.25)',
      }
    },
  },
  plugins: [],
}

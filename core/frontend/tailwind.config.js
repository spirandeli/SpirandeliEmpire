/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'pixel-title': ['"Press Start 2P"', 'monospace'],
        'pixel-body': ['"Pixelify Sans"', 'sans-serif'],
        'pixel-retro': ['"VT323"', 'monospace'],
      },
      colors: {
        rpg: {
          wood: '#2c1a0e',
          woodDark: '#190e07',
          parchment: '#e6c88b',
          stone: '#23272e',
          gold: '#f59e0b',
          mana: '#06b6d4',
          hp: '#ef4444',
          stamina: '#10b981',
        },
        empire: {
          900: '#0b0f19',
          800: '#111827',
          700: '#1f2937',
          600: '#374151',
          gold: '#f59e0b',
          emerald: '#10b981',
          cyan: '#06b6d4',
          danger: '#ef4444'
        }
      }
    },
  },
  plugins: [],
}

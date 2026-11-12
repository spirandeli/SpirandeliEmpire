/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        empire: {
          dark: '#0B0F19',
          card: '#131B2E',
          border: '#1F293D',
          primary: '#6366F1',
          accent: '#06B6D4',
          gold: '#F59E0B'
        }
      }
    },
  },
  plugins: [],
}


/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        fintech: {
          dark: '#090d16',
          card: '#0f172a',
          hover: '#1e293b',
          border: '#334155',
          accent: '#38bdf8',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#f43f5e',
          text: '#f8fafc',
          muted: '#94a3b8'
        }
      }
    },
  },
  plugins: [],
}


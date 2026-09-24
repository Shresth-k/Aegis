/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#090a0f',
        surface: {
          DEFAULT: '#0f1118',
          subtle: '#141722',
          muted: '#1a1e2d',
          border: '#23293d',
          borderHover: '#343d5a',
        },
        brand: {
          cyan: '#06b6d4',
          cyanGlow: '#06b6d420',
          blue: '#3b82f6',
          emerald: '#10b981',
          emeraldGlow: '#10b98120',
          amber: '#f59e0b',
          red: '#ef4444',
          redGlow: '#ef444420',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};

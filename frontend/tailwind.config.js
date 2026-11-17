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
        background: '#050507',
        surface: {
          DEFAULT: '#09090d',
          subtle: '#0f0f14',
          muted: '#14141b',
          border: '#1e1e28',
          borderHover: '#2e2e3d',
        },
        cyber: {
          emerald: '#10b981',
          emeraldGlow: '#10b98133',
          red: '#ef4444',
          redGlow: '#ef444433',
          amber: '#f59e0b',
          amberGlow: '#f59e0b33',
          cyan: '#06b6d4',
          cyanGlow: '#06b6d433',
          blue: '#3b82f6',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'radar-sweep': 'radar 4s linear infinite',
      },
      keyframes: {
        radar: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        }
      }
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Google Sans"', 'Roboto', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        display: ['"Outfit"', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#e8f0fe',
          100: '#d2e3fc',
          200: '#aEcBfa',
          300: '#8ab4f8',
          400: '#669df6',
          500: '#4285f4', // Google Blue
          600: '#1a73e8',
          700: '#1967d2',
          800: '#185abc',
          900: '#174ea6',
        },
        void: '#06060a',
        deep: '#0a0a10',
        surface: '#101018',
        elevated: '#16161f',
        'border-subtle': '#1e1e2a',
        'border-default': '#2a2a3a',
        accent: {
          DEFAULT: '#7c3aed',
          dim: '#5b21b6',
        },
      },
      boxShadow: {
        'google': '0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15)',
        'google-hover': '0 1px 3px 0 rgba(60,64,67,0.3), 0 4px 8px 3px rgba(60,64,67,0.15)',
      }
    },
  },
  plugins: [],
}


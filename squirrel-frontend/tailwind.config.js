/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        // Design System - Background
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'bg-card': 'var(--bg-card)',
        'bg-elevated': 'var(--bg-elevated)',
        'bg-hover': 'var(--bg-hover)',

        // Design System - Text
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-tertiary': 'var(--text-tertiary)',
        'text-muted': 'var(--text-muted)',
        'text-accent': 'var(--text-accent)',

        // Design System - Status Colors
        'color-primary': 'var(--color-primary)',
        'color-primary-hover': 'var(--color-primary-hover)',
        'color-success': 'var(--color-success)',
        'color-success-hover': 'var(--color-success-hover)',
        'color-error': 'var(--color-error)',
        'color-error-hover': 'var(--color-error-hover)',
        'color-warning': 'var(--color-warning)',
        'color-warning-hover': 'var(--color-warning-hover)',
        'color-info': 'var(--color-info)',
        'color-info-hover': 'var(--color-info-hover)',

        // Design System - Border
        'border-primary': 'var(--border-primary)',
        'border-secondary': 'var(--border-secondary)',
        'border-hover': 'var(--border-hover)',

        // Design System - Overlay
        'overlay-dark-50': 'var(--overlay-dark-50)',
        'overlay-dark-70': 'var(--overlay-dark-70)',
        'overlay-dark-75': 'var(--overlay-dark-75)',
      },
      fontSize: {
        '2xs': 'var(--font-size-2xs)',
      },
      spacing: {
        'nav': 'var(--mobile-nav-height)',
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        'full': 'var(--radius-full)',
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
      },
      minWidth: {
        '20': '5rem',
        '24': '6rem',
        '28': '7rem',
        '32': '8rem',
        '36': '9rem',
        '40': '10rem',
        '44': '11rem',
        '48': '12rem',
        '52': '13rem',
        '56': '14rem',
        '60': '15rem',
        '64': '16rem',
        '72': '18rem',
        '80': '20rem',
        '96': '24rem',
        'field': 'var(--min-width-field, 10rem)',
      },
    },
  },
  plugins: [
    function({ addUtilities, addComponents }) {
      // Utilities
      const newUtilities = {
        '.overflow-touch': {
          '-webkit-overflow-scrolling': 'touch',
        },
      }
      addUtilities(newUtilities, ['responsive'])

      // Components - Common button styles
      const buttonComponents = {
        '.btn-base': {
          '@apply inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-primary disabled:opacity-50 disabled:cursor-not-allowed': {},
        },
        '.btn-xs': {
          '@apply px-2 py-1 text-xs rounded': {},
        },
        '.btn-sm': {
          '@apply px-3 py-1.5 text-sm rounded-md': {},
        },
        '.btn-md': {
          '@apply px-4 py-2 text-base rounded-md': {},
        },
        '.btn-lg': {
          '@apply px-6 py-3 text-lg rounded-lg': {},
        },
        '.btn-pill': {
          '@apply rounded-full': {},
        },
        // Input styles
        '.input-base': {
          '@apply w-full bg-bg-secondary border border-border-primary text-text-primary placeholder-text-muted transition-colors duration-150 focus:outline-none focus:ring-1 focus:border-color-info focus:ring-color-info disabled:opacity-50 disabled:cursor-not-allowed': {},
        },
        '.input-sm': {
          '@apply px-2.5 py-1.5 text-xs rounded-md': {},
        },
        '.input-md': {
          '@apply px-3 py-2 text-sm rounded-md': {},
        },
        '.input-lg': {
          '@apply px-4 py-3 text-base rounded-lg': {},
        },
      }
      addComponents(buttonComponents)
    }
  ],
}


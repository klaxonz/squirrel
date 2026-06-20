import type { Config } from 'tailwindcss'
import tailwindcssAnimate from 'tailwindcss-animate'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'var(--font-sans)', 'sans-serif'],
      },
      // Type scale — adds two sub-xs sizes for the deliberate compact-UI
      // labels (9px/10px meta, badges, timestamps) that were previously
      // scattered as `text-[9px]`/`text-[10px]`. The 11px/13px occurrences are
      // NOT given slots: they sit within 1px of the standard 12px (xs) / 14px
      // (sm) and are normalised to those during the fix-up, collapsing the
      // type scale rather than expanding it infinitely.
      //   9px → text-3xs, 10px → text-2xs, 11px → text-xs(12),
      //   12px → text-xs, 13px → text-sm(14), 14px → text-sm
      fontSize: {
        '3xs': ['9px', { lineHeight: '1.2' }],
        '2xs': ['10px', { lineHeight: '1.25' }],
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        success: { DEFAULT: 'hsl(var(--success))', foreground: 'hsl(var(--success-foreground))' },
        warning: { DEFAULT: 'hsl(var(--warning))', foreground: 'hsl(var(--warning-foreground))' },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        sidebar: { DEFAULT: 'hsl(var(--sidebar))', foreground: 'hsl(var(--sidebar-foreground))' },
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
        'md': 'var(--radius)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
      },
      boxShadow: {
        'xs': 'var(--shadow-xs)',
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'premium': 'var(--shadow-premium)',
      },
      // Z-index scale — maps the --z-* tokens to utilities so `z-dialog` /
      // `z-toast` etc. replace the scattered `z-[1300]` magic values.
      // (Tailwind's own `z-auto/0/10/20/30/40/50` are overridden by these.)
      zIndex: {
        'base': 'var(--z-base)',
        'content': 'var(--z-content)',
        'header': 'var(--z-header)',
        'sidebar': 'var(--z-sidebar)',
        'dropdown': 'var(--z-dropdown)',
        'popover': 'var(--z-popover)',
        'sheet': 'var(--z-sheet)',
        'dialog': 'var(--z-dialog)',
        'toast': 'var(--z-toast)',
        'player': 'var(--z-player-overlay)',
      },
      // Motion — bind transition utilities to the shared --duration-* / --ease-*.
      transitionDuration: {
        'fast': 'var(--duration-fast)',
        'base': 'var(--duration-base)',
        'slow': 'var(--duration-slow)',
      },
      transitionTimingFunction: {
        'default': 'var(--ease-default)',
        'out': 'var(--ease-out)',
        'spring': 'var(--ease-spring)',
      },
    },
  },
  plugins: [tailwindcssAnimate],
} satisfies Config

import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Config } from 'tailwindcss'
import tailwindcssAnimate from 'tailwindcss-animate'

// Absolute globs: vite may be invoked with cwd=squirrel-desktop while this
// config lives under renderer/, so relative content paths would miss sources.
const rendererRoot = path.dirname(fileURLToPath(import.meta.url))

export default {
  darkMode: ['class'],
  content: [
    path.join(rendererRoot, 'index.html'),
    path.join(rendererRoot, 'src/**/*.{vue,js,ts,jsx,tsx}'),
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'Georgia', 'serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      // Type scale — adds two sub-xs sizes for the deliberate compact-UI
      // labels (9px/10px meta, badges, timestamps) that were previously
      // scattered as `text-[9px]`/`text-[10px]`. The 11px/13px occurrences are
      // NOT given slots: they sit within 1px of the standard 12px (xs) / 14px
      // (sm) and are normalised to those during the fix-up, collapsing the
      // type scale rather than expanding it infinitely.
      //   9px → text-3xs, 10px → text-2xs, 11px → text-xs(12),
      //   12px → text-xs, 13px → text-sm(14), 14px → text-sm
      //   8px → text-4xs:duration badge 等极小辅助标签的专用档。
      //     ⚠ 教训:不要用 text-[8px] 任意值 —— Tailwind JIT 对小数/小值任意值
      //     编译不稳定(实测 text-[8px] / text-[8.5px] 未进产物,导致 badge 回退
      //     到继承的 12px)。用命名 token 确保 JIT 必定编译。
      fontSize: {
        '4xs': ['8px', { lineHeight: '1.15' }],
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
        overlay: {
          DEFAULT: 'hsl(var(--overlay) / 0.45)',
          strong: 'hsl(var(--overlay) / 0.62)',
        },
        sidebar: { DEFAULT: 'hsl(var(--sidebar))', foreground: 'hsl(var(--sidebar-foreground))', border: 'hsl(var(--sidebar-border))' },
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
      },
      boxShadow: {
        'xs': 'var(--shadow-xs)',
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'premium': 'var(--shadow-premium)',
        'card-hover': 'var(--shadow-card-hover)',
        'surface': 'var(--app-surface-shadow)',
        'primary': '0 1px 2px hsl(var(--primary) / 0.3), 0 0 0 1px hsl(var(--primary) / 0.5) inset',
        'primary-hover': '0 2px 8px hsl(var(--primary) / 0.35)',
        'popover': 'var(--app-floating-shadow)',
        'dialog': 'var(--app-overlay-shadow)',
      },
      backgroundImage: {
        'brand-gradient': 'var(--brand-gradient)',
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

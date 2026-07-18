import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

/**
 * The single visual host for every Squirrel surface.
 *
 * Keep product identity in this preset instead of page-scoped CSS. Layout may
 * still differ between video, RSS, music and operate surfaces, but controls,
 * states, typography and surfaces must all consume this token graph.
 */
export const squirrelAuraPreset = definePreset(Aura, {
  semantic: {
    // Aura is the visual host, while this map gives its neutral surface scale
    // the product's single warm-neutral color axis. Without this mapping,
    // page surfaces sourced from the legacy semantic tokens and controls
    // sourced from Aura's Zinc defaults render as two unrelated dark themes.
    colorScheme: {
      light: {
        surface: {
          0: 'hsl(var(--card))',
          50: 'hsl(var(--gray-50))',
          100: 'hsl(var(--gray-100))',
          200: 'hsl(var(--gray-200))',
          300: 'hsl(var(--gray-300))',
          400: 'hsl(var(--gray-400))',
          500: 'hsl(var(--gray-500))',
          600: 'hsl(var(--gray-600))',
          700: 'hsl(var(--gray-700))',
          800: 'hsl(var(--gray-800))',
          900: 'hsl(var(--gray-900))',
          950: 'hsl(var(--gray-950))',
        },
      },
      dark: {
        surface: {
          0: 'hsl(var(--foreground))',
          50: 'hsl(var(--gray-50))',
          100: 'hsl(var(--gray-100))',
          200: 'hsl(var(--gray-200))',
          300: 'hsl(var(--gray-300))',
          400: 'hsl(var(--gray-400))',
          500: 'hsl(var(--gray-500))',
          600: 'hsl(var(--gray-600))',
          700: 'hsl(var(--gray-700))',
          800: 'hsl(var(--gray-800))',
          900: 'hsl(var(--gray-900))',
          950: 'hsl(var(--gray-950))',
        },
      },
    },
    typography: {
      fontFamily: 'var(--font-sans)',
      fontSize: '0.875rem',
      lineHeight: '1.45',
    },
    primary: {
      50: '{orange.50}',
      100: '{orange.100}',
      200: '{orange.200}',
      300: '{orange.300}',
      400: '{orange.400}',
      500: '{orange.500}',
      600: '{orange.600}',
      700: '{orange.700}',
      800: '{orange.800}',
      900: '{orange.900}',
      950: '{orange.950}',
      color: 'light-dark({primary.600}, {primary.400})',
      contrastColor: 'light-dark(#ffffff, {surface.950})',
      hoverColor: 'light-dark({primary.700}, {primary.300})',
      activeColor: 'light-dark({primary.800}, {primary.200})',
    },
    focusRing: {
      width: '2px',
      style: 'solid',
      color: 'color-mix(in srgb, {primary.color}, transparent 25%)',
      offset: '2px',
      shadow: 'none',
    },
    formField: {
      background: 'light-dark({surface.0}, {surface.950})',
      filledBackground: 'light-dark({surface.50}, {surface.900})',
      filledHoverBackground: 'light-dark({surface.100}, {surface.800})',
      filledFocusBackground: 'light-dark({surface.0}, {surface.900})',
      borderColor: 'light-dark({surface.300}, {surface.700})',
      hoverBorderColor: 'light-dark({surface.400}, {surface.600})',
      focusBorderColor: '{primary.color}',
      borderRadius: '{border.radius.md}',
      transitionDuration: '{transition.duration}',
    },
  },
})

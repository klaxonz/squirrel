import { useTheme } from './useTheme'

export {
  useTheme,
  type ThemeName,
  type ThemeColors,
  type ThemeConfig,
  type UseThemeOptions,
  type UseThemeReturn
} from './useTheme'

export const themeFiles = {
  variables: () => import('./variables.css'),
  base: () => import('./base.css'),
  dark: () => import('./dark.css'),
  light: () => import('./light.css'),
}

export const presets = {
  red: {
    name: 'dark' as const,
    colors: {
      primary: '#ff0000',
      primaryHover: '#ff3333',
      primaryActive: '#cc0000'
    }
  },

  cyan: {
    name: 'dark' as const,
    colors: {
      primary: '#00a1d6',
      primaryHover: '#00b5e5',
      primaryActive: '#0091c2'
    }
  },

  crimson: {
    name: 'dark' as const,
    colors: {
      primary: '#e50914',
      primaryHover: '#f40612',
      primaryActive: '#b20710'
    }
  },

  green: {
    name: 'dark' as const,
    colors: {
      primary: '#4caf50',
      primaryHover: '#66bb6a',
      primaryActive: '#388e3c'
    }
  },

  purple: {
    name: 'dark' as const,
    colors: {
      primary: '#9c27b0',
      primaryHover: '#ab47bc',
      primaryActive: '#7b1fa2'
    }
  }
}

export default useTheme

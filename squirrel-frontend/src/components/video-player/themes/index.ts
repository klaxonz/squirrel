import { useTheme } from './useTheme'

export {
  useTheme,
  type ThemeName,
  type ThemeColors,
  type ThemeConfig,
  type UseThemeOptions,
  type UseThemeReturn
} from './useTheme'

// CSS 文件路径（用于动态导入）
export const themeFiles = {
  variables: () => import('./variables.css'),
  base: () => import('./base.css'),
  dark: () => import('./dark.css'),
  light: () => import('./light.css')
}

// 预设主题配置
export const presets = {
  // YouTube 风格
  youtube: {
    name: 'dark' as const,
    colors: {
      primary: '#ff0000',
      primaryHover: '#ff3333',
      primaryActive: '#cc0000'
    }
  },
  
  // Bilibili 风格
  bilibili: {
    name: 'dark' as const,
    colors: {
      primary: '#00a1d6',
      primaryHover: '#00b5e5',
      primaryActive: '#0091c2'
    }
  },
  
  // Netflix 风格
  netflix: {
    name: 'dark' as const,
    colors: {
      primary: '#e50914',
      primaryHover: '#f40612',
      primaryActive: '#b20710'
    }
  },
  
  // 绿色主题
  green: {
    name: 'dark' as const,
    colors: {
      primary: '#4caf50',
      primaryHover: '#66bb6a',
      primaryActive: '#388e3c'
    }
  },
  
  // 紫色主题
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

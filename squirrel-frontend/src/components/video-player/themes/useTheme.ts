/**
 * 主题管理 Composable
 * 支持主题切换、自定义 CSS 变量、预设主题
 */

import { ref, computed, watch, onMounted, type Ref } from 'vue'

export type ThemeName = 'dark' | 'light' | 'auto' | 'custom'

export interface ThemeColors {
  primary?: string
  primaryHover?: string
  primaryActive?: string
  bg?: string
  bgElevated?: string
  bgOverlay?: string
  bgHover?: string
  bgActive?: string
  text?: string
  textSecondary?: string
  textTertiary?: string
  textDisabled?: string
  border?: string
  borderHover?: string
}

export interface ThemeConfig {
  name?: ThemeName
  colors?: ThemeColors
  customVariables?: Record<string, string>
}

export interface UseThemeOptions {
  defaultTheme?: ThemeName
  storageKey?: string
  syncWithSystem?: boolean
}

export interface UseThemeReturn {
  theme: Ref<ThemeName>
  isDark: Ref<boolean>
  setTheme: (theme: ThemeName) => void
  setColors: (colors: ThemeColors) => void
  setVariable: (name: string, value: string) => void
  getVariable: (name: string) => string
  applyConfig: (config: ThemeConfig) => void
  resetToDefault: () => void
}

// CSS 变量名映射
const COLOR_VAR_MAP: Record<keyof ThemeColors, string> = {
  primary: '--sp-primary',
  primaryHover: '--sp-primary-hover',
  primaryActive: '--sp-primary-active',
  bg: '--sp-bg',
  bgElevated: '--sp-bg-elevated',
  bgOverlay: '--sp-bg-overlay',
  bgHover: '--sp-bg-hover',
  bgActive: '--sp-bg-active',
  text: '--sp-text',
  textSecondary: '--sp-text-secondary',
  textTertiary: '--sp-text-tertiary',
  textDisabled: '--sp-text-disabled',
  border: '--sp-border',
  borderHover: '--sp-border-hover'
}

/**
 * 检测系统主题偏好
 */
function getSystemTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * 主题管理 Composable
 */
export function useTheme(options: UseThemeOptions = {}): UseThemeReturn {
  const {
    defaultTheme = 'dark',
    storageKey = 'sp-theme',
    syncWithSystem = true
  } = options

  const theme = ref<ThemeName>(defaultTheme)
  const systemTheme = ref<'dark' | 'light'>(getSystemTheme())

  // 计算实际主题
  const isDark = computed(() => {
    if (theme.value === 'auto') {
      return systemTheme.value === 'dark'
    }
    return theme.value === 'dark'
  })

  // 应用主题到 DOM
  const applyTheme = (themeName: ThemeName) => {
    if (typeof document === 'undefined') return

    const root = document.documentElement
    
    // 移除旧主题类
    root.classList.remove('sp-theme-dark', 'sp-theme-light')
    root.removeAttribute('data-sp-theme')

    // 应用新主题
    const actualTheme = themeName === 'auto' ? systemTheme.value : themeName
    if (actualTheme === 'dark' || actualTheme === 'light') {
      root.classList.add(`sp-theme-${actualTheme}`)
      root.setAttribute('data-sp-theme', actualTheme)
    }
  }

  // 设置主题
  const setTheme = (newTheme: ThemeName) => {
    theme.value = newTheme
    applyTheme(newTheme)
    
    // 持久化
    if (typeof localStorage !== 'undefined' && storageKey) {
      localStorage.setItem(storageKey, newTheme)
    }
  }

  // 设置颜色
  const setColors = (colors: ThemeColors) => {
    if (typeof document === 'undefined') return

    const root = document.documentElement
    Object.entries(colors).forEach(([key, value]) => {
      if (value && COLOR_VAR_MAP[key as keyof ThemeColors]) {
        root.style.setProperty(COLOR_VAR_MAP[key as keyof ThemeColors], value)
      }
    })
  }

  // 设置单个变量
  const setVariable = (name: string, value: string) => {
    if (typeof document === 'undefined') return
    
    const varName = name.startsWith('--') ? name : `--sp-${name}`
    document.documentElement.style.setProperty(varName, value)
  }

  // 获取变量值
  const getVariable = (name: string): string => {
    if (typeof document === 'undefined') return ''
    
    const varName = name.startsWith('--') ? name : `--sp-${name}`
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  }

  // 应用完整配置
  const applyConfig = (config: ThemeConfig) => {
    if (config.name) {
      setTheme(config.name)
    }
    if (config.colors) {
      setColors(config.colors)
    }
    if (config.customVariables) {
      Object.entries(config.customVariables).forEach(([name, value]) => {
        setVariable(name, value)
      })
    }
  }

  // 重置到默认
  const resetToDefault = () => {
    if (typeof document === 'undefined') return

    // 移除所有自定义样式
    document.documentElement.removeAttribute('style')
    
    // 重置主题
    setTheme(defaultTheme)
  }

  // 监听系统主题变化
  onMounted(() => {
    // 从 localStorage 恢复主题
    if (typeof localStorage !== 'undefined' && storageKey) {
      const saved = localStorage.getItem(storageKey) as ThemeName | null
      if (saved) {
        theme.value = saved
      }
    }

    // 应用初始主题
    applyTheme(theme.value)

    // 监听系统主题变化
    if (syncWithSystem && typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      
      const handleChange = (e: MediaQueryListEvent) => {
        systemTheme.value = e.matches ? 'dark' : 'light'
        if (theme.value === 'auto') {
          applyTheme('auto')
        }
      }

      mediaQuery.addEventListener('change', handleChange)
    }
  })

  // 监听主题变化
  watch(theme, (newTheme) => {
    applyTheme(newTheme)
  })

  return {
    theme,
    isDark,
    setTheme,
    setColors,
    setVariable,
    getVariable,
    applyConfig,
    resetToDefault
  }
}

export default useTheme

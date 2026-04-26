import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { APP_THEME_STORAGE_KEY, resolveEffectiveTheme, resolveStoredThemeMode, shouldUseDarkTheme, type AppThemeMode } from '@/lib/theme'

export const useThemeStore = defineStore('theme', () => {
  const themeMode = ref<AppThemeMode>('system')
  const systemTheme = ref<'light' | 'dark'>('light')

  const effectiveTheme = computed(() => resolveEffectiveTheme(themeMode.value, systemTheme.value))
  const isDark = computed(() => shouldUseDarkTheme(themeMode.value, systemTheme.value))

  const init = () => {
    themeMode.value = resolveStoredThemeMode(localStorage.getItem(APP_THEME_STORAGE_KEY))
    systemTheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    apply()
  }

  const apply = () => {
    document.documentElement.classList.toggle('dark', isDark.value)
    document.documentElement.dataset.theme = effectiveTheme.value
  }

  const setThemeMode = (mode: AppThemeMode) => {
    themeMode.value = mode
    localStorage.setItem(APP_THEME_STORAGE_KEY, mode)
    apply()
  }

  return {
    themeMode,
    systemTheme,
    effectiveTheme,
    isDark,
    init,
    setThemeMode
  }
})

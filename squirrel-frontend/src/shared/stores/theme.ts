import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { APP_THEME_STORAGE_KEY, resolveEffectiveTheme, resolveStoredThemeMode, shouldUseDarkTheme, type AppThemeMode } from '@/shared/lib/theme'

export const useThemeStore = defineStore('theme', () => {
  const themeMode = ref<AppThemeMode>('system')
  const systemTheme = ref<'light' | 'dark'>('light')

  const effectiveTheme = computed(() => resolveEffectiveTheme(themeMode.value, systemTheme.value))
  const isDark = computed(() => shouldUseDarkTheme(themeMode.value, systemTheme.value))

  // ponytail: single source of truth for OS color-scheme changes. Previously
  // only the now-deleted useAppTheme composable wired this listener, so the
  // store path (main.ts / AppLayout) never reacted to OS dark-mode flips.
  let mediaQuery: MediaQueryList | null = null
  let mediaQueryHandler: ((event: MediaQueryListEvent) => void) | null = null

  const watchSystemTheme = () => {
    if (typeof window === 'undefined' || mediaQuery) return
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQueryHandler = (event) => {
      systemTheme.value = event.matches ? 'dark' : 'light'
      apply()
    }
    mediaQuery.addEventListener('change', mediaQueryHandler)
  }

  const init = () => {
    themeMode.value = resolveStoredThemeMode(localStorage.getItem(APP_THEME_STORAGE_KEY))
    systemTheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    watchSystemTheme()
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

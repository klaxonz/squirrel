import { computed, ref } from 'vue'

import {
  APP_THEME_STORAGE_KEY,
  resolveEffectiveTheme,
  resolveStoredThemeMode,
  shouldUseDarkTheme,
  type AppThemeMode,
} from '@/lib/theme'

const themeMode = ref<AppThemeMode>('system')
const systemTheme = ref<'light' | 'dark'>('light')
const isReady = ref(false)

let mediaQuery: MediaQueryList | null = null
let mediaQueryHandler: ((event: MediaQueryListEvent) => void) | null = null

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') {
    return 'light'
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme() {
  if (typeof document === 'undefined') {
    return
  }

  const root = document.documentElement
  const effectiveTheme = resolveEffectiveTheme(themeMode.value, systemTheme.value)
  const isDark = shouldUseDarkTheme(themeMode.value, systemTheme.value)

  root.classList.toggle('dark', isDark)
  root.dataset.theme = effectiveTheme
  root.style.colorScheme = effectiveTheme
}

function ensureMediaQuery() {
  if (typeof window === 'undefined' || mediaQuery) {
    return
  }

  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQueryHandler = (event: MediaQueryListEvent) => {
    systemTheme.value = event.matches ? 'dark' : 'light'
    applyTheme()
  }
  mediaQuery.addEventListener('change', mediaQueryHandler)
}

function readStoredThemeMode(): AppThemeMode {
  if (typeof window === 'undefined') {
    return 'system'
  }

  return resolveStoredThemeMode(window.localStorage.getItem(APP_THEME_STORAGE_KEY))
}

function persistThemeMode(mode: AppThemeMode) {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(APP_THEME_STORAGE_KEY, mode)
}

export function initializeAppTheme() {
  if (isReady.value) {
    applyTheme()
    return
  }

  themeMode.value = readStoredThemeMode()
  systemTheme.value = getSystemTheme()
  ensureMediaQuery()
  applyTheme()
  isReady.value = true
}

export function useAppTheme() {
  if (!isReady.value) {
    initializeAppTheme()
  }

  const effectiveTheme = computed(() =>
    resolveEffectiveTheme(themeMode.value, systemTheme.value),
  )

  const setThemeMode = (mode: AppThemeMode) => {
    themeMode.value = mode
    persistThemeMode(mode)
    applyTheme()
  }

  return {
    themeMode,
    systemTheme,
    effectiveTheme,
    setThemeMode,
  }
}

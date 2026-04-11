export const APP_THEME_STORAGE_KEY = 'squirrel-app-theme'

export type AppThemeMode = 'light' | 'dark' | 'system' | 'cyber' | 'scifi'
export type EffectiveTheme = 'light' | 'dark' | 'cyber' | 'scifi'

export function isAppThemeMode(value: unknown): value is AppThemeMode {
  return (
    value === 'light' ||
    value === 'dark' ||
    value === 'system' ||
    value === 'cyber' ||
    value === 'scifi'
  )
}

export function resolveStoredThemeMode(value: unknown): AppThemeMode {
  return isAppThemeMode(value) ? value : 'system'
}

export function resolveEffectiveTheme(
  mode: AppThemeMode,
  systemTheme: 'light' | 'dark',
): EffectiveTheme {
  if (mode === 'system') {
    return systemTheme
  }
  return mode
}

export function shouldUseDarkTheme(
  mode: AppThemeMode,
  systemTheme: 'light' | 'dark',
): boolean {
  const effective = resolveEffectiveTheme(mode, systemTheme)
  return effective === 'dark' || effective === 'cyber' || effective === 'scifi'
}

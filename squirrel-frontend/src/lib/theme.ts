export const APP_THEME_STORAGE_KEY = 'squirrel-app-theme'

export type AppThemeMode = 'light' | 'dark' | 'system'
export type EffectiveTheme = 'light' | 'dark'

export function isAppThemeMode(value: unknown): value is AppThemeMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

export function resolveStoredThemeMode(value: unknown): AppThemeMode {
  return isAppThemeMode(value) ? value : 'system'
}

export function resolveEffectiveTheme(
  mode: AppThemeMode,
  systemTheme: EffectiveTheme,
): EffectiveTheme {
  return mode === 'system' ? systemTheme : mode
}

export function shouldUseDarkTheme(
  mode: AppThemeMode,
  systemTheme: EffectiveTheme,
): boolean {
  return resolveEffectiveTheme(mode, systemTheme) === 'dark'
}

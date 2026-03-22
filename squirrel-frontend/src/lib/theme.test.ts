import assert from 'node:assert/strict'
import test from 'node:test'

import {
  APP_THEME_STORAGE_KEY,
  isAppThemeMode,
  resolveEffectiveTheme,
  resolveStoredThemeMode,
  shouldUseDarkTheme,
} from './theme.ts'

test('APP_THEME_STORAGE_KEY is stable', () => {
  assert.equal(APP_THEME_STORAGE_KEY, 'squirrel-app-theme')
})

test('isAppThemeMode accepts supported values only', () => {
  assert.equal(isAppThemeMode('light'), true)
  assert.equal(isAppThemeMode('dark'), true)
  assert.equal(isAppThemeMode('system'), true)
  assert.equal(isAppThemeMode('auto'), false)
  assert.equal(isAppThemeMode(''), false)
})

test('resolveStoredThemeMode returns supported explicit modes', () => {
  assert.equal(resolveStoredThemeMode('light'), 'light')
  assert.equal(resolveStoredThemeMode('dark'), 'dark')
  assert.equal(resolveStoredThemeMode('system'), 'system')
})

test('resolveStoredThemeMode falls back to system for invalid values', () => {
  assert.equal(resolveStoredThemeMode(null), 'system')
  assert.equal(resolveStoredThemeMode(undefined), 'system')
  assert.equal(resolveStoredThemeMode('auto'), 'system')
  assert.equal(resolveStoredThemeMode('cinema'), 'system')
})

test('resolveEffectiveTheme respects explicit theme modes', () => {
  assert.equal(resolveEffectiveTheme('light', 'dark'), 'light')
  assert.equal(resolveEffectiveTheme('dark', 'light'), 'dark')
})

test('resolveEffectiveTheme uses system preference for system mode', () => {
  assert.equal(resolveEffectiveTheme('system', 'light'), 'light')
  assert.equal(resolveEffectiveTheme('system', 'dark'), 'dark')
})

test('shouldUseDarkTheme reflects the effective theme', () => {
  assert.equal(shouldUseDarkTheme('dark', 'light'), true)
  assert.equal(shouldUseDarkTheme('light', 'dark'), false)
  assert.equal(shouldUseDarkTheme('system', 'dark'), true)
  assert.equal(shouldUseDarkTheme('system', 'light'), false)
})

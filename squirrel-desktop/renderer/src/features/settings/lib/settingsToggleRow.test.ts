import { describe, expect, it } from 'vitest'
import { canToggleSettingsRow, nextSettingsToggleValue } from './settingsToggleRow'

describe('settingsToggleRow', () => {
  it('blocks toggles while disabled', () => {
    expect(canToggleSettingsRow(true)).toBe(false)
    expect(nextSettingsToggleValue(true, true)).toBeNull()
    expect(nextSettingsToggleValue(false, true)).toBeNull()
  })

  it('flips boolean when enabled', () => {
    expect(canToggleSettingsRow(false)).toBe(true)
    expect(nextSettingsToggleValue(false, false)).toBe(true)
    expect(nextSettingsToggleValue(true, false)).toBe(false)
  })
})

/**
 * Operate settings: whole-row toggle helpers.
 * Row click flips the value; Switch uses stopPropagation to avoid double-toggle.
 */

export function canToggleSettingsRow(disabled: boolean): boolean {
  return !disabled
}

export function nextSettingsToggleValue(
  current: boolean,
  disabled: boolean,
): boolean | null {
  if (!canToggleSettingsRow(disabled)) return null
  return !current
}

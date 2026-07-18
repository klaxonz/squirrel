import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

describe('settings operate row contract', () => {
  const view = read('../views/Settings.vue')
  const layout = read('../../../shared/styles/layout.css')
  const helper = read('./settingsToggleRow.ts')

  it('makes boolean setting rows whole-row toggleable without double-firing Switch', () => {
    expect(layout).toContain('app-settings-row--toggle')
    expect(view).toContain('app-settings-row--toggle')
    expect(view).toContain('@click.stop')
    expect(view).toContain('toggleUserSettingRow')
    expect(view).toContain('toggleSystemSettingRow')
    expect(view).toContain('nextSettingsToggleValue')
    expect(helper).toContain('export function nextSettingsToggleValue')
  })

  it('uses the shared settings preset and the six public settings routes', () => {
    expect(view).toContain('preset="settings"')
    expect(view).toContain('settings-nav__item')
    expect(view).toContain('SETTINGS_TABS')
    expect(view).toContain('v-for="tab in settingsTabs"')
    expect(view).not.toContain('AppSectionNav')
    expect(layout).toMatch(/\.app-settings-row\s*\{[^}]*min-height:\s*3\.25rem;/s)
  })

  it('does not throw when leaving the settings tree (blank-page regression)', () => {
    // App.vue Transition mode=out-in keeps Settings mounted while route.name
    // already points at the destination. Throwing on unknown route names
    // aborts enter and leaves an empty stage after sidebar navigation.
    expect(view).not.toMatch(/throw new Error\(`\[Settings\] Unknown settings route/)
    expect(view).toContain('getSettingsTabByRouteName(route.name) ?? defaultSettingsTab')
  })
})

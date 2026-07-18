import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

describe('Fluent Reader RSS workspace contract', () => {
  const listItem = read('../../../shared/components/layout/AppSelectableListItem.vue')
  const workbench = read('../../../shared/components/layout/AppTwoColumnLayout.vue')
  const rssView = read('../views/RssSources.vue')
  const nav = read('./rssEntryNav.ts')

  it('provides a flush continuous-list variant for entry rows', () => {
    expect(listItem).toMatch(/variant\?:\s*'default'\s*\|\s*'flush'/)
    expect(listItem).toContain('app-selectable-list-item--flush')
    expect(listItem).toMatch(/box-shadow:\s*inset 3px 0 0/)
  })

  it('uses flush entry rows and Fluent j/k navigation in the RSS workspace', () => {
    expect(rssView).toContain('variant="flush"')
    expect(rssView).toContain('handleWorkspaceKeyDown')
    expect(rssView).toContain("event.key === 'j'")
    expect(rssView).toContain("event.key === 'k'")
    expect(rssView).toContain('nextEntryIndex')
    expect(nav).toContain('export function nextEntryIndex')
  })

  it('keeps the source column quiet and reader-width', () => {
    expect(rssView).toContain('preset="rss"')
    expect(workbench).toMatch(/app-two-column--preset-rss[^}]*--app-workbench-sidebar-width:\s*15\.5rem/s)
    expect(rssView).toContain('rss-sync-status__menu')
    expect(rssView).not.toContain('轻量同步</span>')
    expect(rssView).not.toMatch(/rss-sync-status__actions/)
  })
})

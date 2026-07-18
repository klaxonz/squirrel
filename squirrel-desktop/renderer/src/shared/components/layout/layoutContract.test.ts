import { readdirSync, readFileSync } from 'node:fs'
import { extname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { NAV_GROUPS, SETTINGS_TABS } from '@/shared/constants/sidebar'

const srcRoot = new URL('../../../', import.meta.url)

const read = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

function collectStyleSources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) {
      return collectStyleSources(path)
    }
    return ['.css', '.vue'].includes(extname(entry.name)) ? [path] : []
  })
}

describe('application layout contract', () => {
  it('keeps the three shell groups and six settings routes as single sources of truth', () => {
    expect(NAV_GROUPS.map((group) => group.key)).toEqual(['media', 'library', 'system'])
    expect(NAV_GROUPS.find((group) => group.key === 'system')?.items.map((item) => item.key))
      .toEqual(['site-runtimes', 'scheduled-tasks', 'logs'])
    expect(SETTINGS_TABS.map((tab) => tab.key)).toEqual([
      'appearance',
      'content',
      'playback',
      'security',
      'system',
      'server',
    ])
  })

  it('exposes named page-width and workbench presets instead of arbitrary dimensions', () => {
    const pageShell = read('./AppPageShell.vue')
    const workbench = read('./AppTwoColumnLayout.vue')

    expect(pageShell).toContain("surface?: 'consume' | 'organize' | 'operate' | 'immersive'")
    expect(pageShell).toContain("width?: 'media' | 'table' | 'form' | 'reading' | 'fluid'")
    expect(workbench).toContain("preset?: 'settings' | 'playlist' | 'music' | 'rss'")
    expect(workbench).not.toMatch(/sidebarWidth|contentWidth/)
  })

  it('does not ship text smaller than the 11px badge floor', () => {
    const violations: string[] = []
    const rootPath = fileURLToPath(srcRoot)

    for (const file of collectStyleSources(rootPath)) {
      const source = readFileSync(file, 'utf8')
      for (const match of source.matchAll(/font-size:\s*(\d*\.?\d+)(rem|px)/g)) {
        const value = Number(match[1])
        const pixels = match[2] === 'rem' ? value * 16 : value
        if (pixels < 11) {
          violations.push(`${relative(rootPath, file)}: ${match[0]}`)
        }
      }
    }

    expect(violations).toEqual([])
  })
})

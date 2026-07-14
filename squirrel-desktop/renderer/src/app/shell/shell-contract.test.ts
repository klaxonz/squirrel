/** Locks documented shell geometry to the global tokens consumed by Vue SFCs. */
import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

const source = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

describe('desktop shell geometry contract', () => {
  it('keeps the documented shell dimensions in the global token layer', async () => {
    const css = await source('../../shared/styles/layout.css')

    expect(css).toMatch(/--app-titlebar-height:\s*2rem;/)
    expect(css).toMatch(/--app-header-height:\s*3\.25rem;/)
    expect(css).toMatch(/--sidebar-expanded-width:\s*15rem;/)
    expect(css).toMatch(/--sidebar-item-height:\s*2\.25rem;/)
    expect(css).toMatch(/--sidebar-icon-size:\s*1\.25rem;/)
  })

  it('requires shell components to consume shared geometry tokens', async () => {
    const [titleBar, header, sidebarItem] = await Promise.all([
      source('./DesktopTitleBar.vue'),
      source('./AppHeader.vue'),
      source('../../shared/components/layout/SidebarMenuItem.vue'),
    ])

    expect(titleBar).toMatch(/height:\s*var\(--app-titlebar-height\);/)
    expect(header).toMatch(/height:\s*var\(--app-header-height\);/)
    expect(sidebarItem).toMatch(/height:\s*var\(--sidebar-item-height\);/)
    expect(sidebarItem.match(/var\(--sidebar-icon-size\)/g)).toHaveLength(2)
  })
})

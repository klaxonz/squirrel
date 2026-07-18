/**
 * Source-level contract for the YesPlayMusic-hosted global player geometry.
 * Runtime behavior is covered by the real Electron visual scenario; these
 * assertions keep the frozen dimensions and route variants explicit.
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const sharedLayout = readSource('../../../shared/styles/layout.css')
const player = readSource('../components/GlobalMusicPlayerBar.vue')
const queuePanel = readSource('../components/player/MusicQueuePanel.vue')
const appLayout = readSource('../../../app/layouts/AppLayout.vue')
const router = readSource('../../../app/router/index.ts')

function cssRules(source: string, selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`${escaped}\\s*\\{(?<rules>[^}]*)\\}`))?.groups?.rules ?? ''
}

describe('music player layout contract', () => {
  it('freezes the YesPlayMusic player height at 64px', () => {
    expect(sharedLayout).toMatch(/--app-music-player-height:\s*4rem;/)
  })

  it('shortens recoverable playback errors so the three-up bar stays intact', () => {
    const trackInfo = readSource('../components/player/MusicBarTrackInfo.vue')
    expect(trackInfo).toContain('shortError')
    expect(trackInfo).toContain('需重新登录')
    // Auth errors offer a clickable path into Music profile login.
    expect(trackInfo).toContain('needsRelogin')
    expect(trackInfo).toMatch(/name:\s*['"]Music['"]/)
  })

  it('uses a flat, full-viewport, fixed bottom bar on the Music surface', () => {
    const rules = cssRules(player, '.music-bar')

    expect(rules).toMatch(/position:\s*fixed;/)
    expect(rules).toMatch(/right:\s*0;/)
    expect(rules).toMatch(/bottom:\s*0;/)
    expect(rules).toMatch(/left:\s*0;/)
    expect(rules).toMatch(/height:\s*var\(--app-music-player-height\);/)
    expect(rules).toMatch(/border-top:\s*1px solid var\(--app-hairline\);/)
    expect(rules).not.toMatch(/border-radius|box-shadow|transform|max-width/)
  })

  it('keeps progress on the top edge and divides controls into three equal regions', () => {
    const innerRules = cssRules(player, '.music-bar-inner')
    const progressRules = cssRules(player, '.music-bar :deep(.music-progress-bar)')

    expect(innerRules).toMatch(/display:\s*grid;/)
    expect(innerRules).toMatch(/grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\);/)
    expect(progressRules).toMatch(/position:\s*absolute;/)
    expect(progressRules).toMatch(/top:\s*0;/)
    expect(progressRules).toMatch(/width:\s*100%;/)
    expect(progressRules).toMatch(/margin:\s*0;/)
  })

  it('preserves the sidebar mini and collapsed dock variants outside Music', () => {
    const miniRules = cssRules(player, '.music-bar--mini')
    const dockRules = cssRules(player, '.music-bar--dock')

    expect(miniRules).toMatch(/width:\s*var\(--sidebar-expanded-width\);/)
    expect(miniRules).toMatch(/height:\s*auto;/)
    expect(dockRules).toMatch(/left:\s*var\(--space-3\);/)
    expect(dockRules).toMatch(/border-radius:\s*var\(--app-surface-radius\);/)
  })

  it('reserves the same tokenized height for every visible player state', () => {
    expect(appLayout).toContain("? 'app-layout__scroll--music-player' : ''")
    expect(appLayout).toMatch(/musicPlayerStore\.resolvingUrl \|\| musicPlayerStore\.audioSrc \|\| musicPlayerStore\.error/)
    expect(cssRules(appLayout, '.app-layout__scroll--music-player')).toMatch(
      /padding-bottom:\s*var\(--app-music-player-height\);/,
    )
    expect(cssRules(queuePanel, '.music-queue-panel')).toMatch(
      /bottom:\s*calc\(var\(--app-music-player-height\) \+ var\(--space-2\)\);/,
    )
  })

  it('reuses the Music instance across query-backed subviews', () => {
    expect(router).toMatch(/path:\s*['"]\/music['"][\s\S]*?transitionKey:\s*['"]music['"]/)
  })
})

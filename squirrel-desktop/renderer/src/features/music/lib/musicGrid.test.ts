/**
 * Source-level contract for the reusable music artwork wall.
 *
 * Keep this DOM-free: its purpose is to make grid geometry and adoption
 * explicit without mounting the individual data-driven views.
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const sharedLayout = readSource('../../../shared/styles/layout.css')

describe('music artwork grid contract', () => {
  it('sets the YesPlayMusic density minimum to 180px', () => {
    expect(sharedLayout).toMatch(/--app-music-grid-min:\s*180px;/)
  })

  it('defines one responsive app-music-grid implementation', () => {
    const gridRules = sharedLayout.match(/\.app-music-grid\s*\{(?<rules>[^}]*)\}/)?.groups?.rules

    expect(gridRules).toBeDefined()
    expect(gridRules).toMatch(/display:\s*grid;/)
    expect(gridRules).toMatch(/gap:\s*var\(--app-music-grid-gap\);/)
    expect(gridRules).toMatch(
      /grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(min\(100%,\s*var\(--app-music-grid-min\)\),\s*1fr\)\);/,
    )
  })

  it.each([
    ['shared MusicCardGrid primitive', '../components/shared/MusicCardGrid.vue'],
    ['playlist discovery wall', '../components/MusicPlaylistGrid.vue'],
    ['rank discovery wall', '../components/MusicRankGrid.vue'],
    ['profile playlist walls', '../components/MusicProfileView.vue'],
    ['artist album wall', '../components/MusicArtistDetailView.vue'],
    ['similar playlist wall', '../components/MusicPlaylistDetailView.vue'],
  ])('%s uses the shared app-music-grid class', (_label, relativePath) => {
    expect(readSource(relativePath)).toContain('class="app-music-grid"')
  })

  it.each([
    ['album discovery wall', '../components/MusicAlbumGrid.vue'],
    ['home recommendation and album walls', '../components/home/MusicHomeView.vue'],
  ])('%s composes the MusicCardGrid primitive', (_label, relativePath) => {
    expect(readSource(relativePath)).toContain('<MusicCardGrid')
  })
})

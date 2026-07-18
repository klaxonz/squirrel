import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const player = readSource('./components/video-player/VideoPlayer.vue')
const settings = readSource('./components/video-player/SettingsMenu.vue')
const themeVariables = readSource('./components/video-player/themes/variables.css')
const lightTheme = readSource('./components/video-player/themes/light.css')
const playbackPage = readSource('./views/VideoPlay.vue')

describe('FreeTube and Artplayer playback anchor contract', () => {
  it('keeps the video canvas unframed like the FreeTube watch surface', () => {
    expect(playbackPage).toMatch(/\.video-player-stage\s*\{[^}]*border:\s*0;[^}]*border-radius:\s*0;/s)
    expect(playbackPage).toMatch(/\.video-player-stage\.is-widescreen\s*\{[^}]*border-radius:\s*0;/s)
  })

  it('uses only the official bottom readability gradient and no glow skin', () => {
    const chrome = [player, settings, themeVariables].join('\n')

    expect(player).toContain('background: linear-gradient(to top, #000, rgb(0 0 0 / 40%), transparent);')
    expect(player.match(/(?:linear|radial)-gradient/g)).toHaveLength(1)
    expect(chrome).not.toMatch(/sp-vignette-overlay|sp-volume-glow|radial-gradient/)
    expect(chrome).not.toMatch(/box-shadow:\s*0\s+0\s+[1-9]/)
    expect(chrome).not.toMatch(/text-shadow:\s*0\s+0\s+[1-9]/)
    expect(settings).not.toContain('.sp-settings-pop::before')
  })

  it('keeps player chrome dark and neutral in the app light theme', () => {
    expect(lightTheme).toContain('--sp-menu-bg: rgba(10, 10, 10, 0.88);')
    expect(lightTheme).toContain('--sp-text: #ffffff;')
    expect(lightTheme).not.toMatch(/252, 247, 240|246, 239, 230|linear-gradient/)
  })

  it('does not render a hanging meta separator when site is empty', () => {
    expect(playbackPage).toMatch(/v-if="videoPublishedText && video\.site"/)
    expect(playbackPage).toMatch(/v-if="videoPublishedText \|\| video\.site"/)
  })
})

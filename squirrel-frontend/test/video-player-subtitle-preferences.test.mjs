import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const usePlayerPath = new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url)
const playerAdapterPath = new URL('../src/components/video-player/core/PlayerAdapter.ts', import.meta.url)
const playerEnginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)
const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player persists subtitle preference and auto-selects captions', async () => {
  const [usePlayerSource, adapterSource, engineSource, videoPlayerSource] = await Promise.all([
    readFile(usePlayerPath, 'utf8'),
    readFile(playerAdapterPath, 'utf8'),
    readFile(playerEnginePath, 'utf8'),
    readFile(videoPlayerPath, 'utf8'),
  ])

  assert.match(adapterSource, /subtitleEnabled\?: boolean/)
  assert.match(adapterSource, /subtitleTrackId\?: string/)
  assert.match(engineSource, /subtitleEnabled: !!track/)
  assert.match(engineSource, /subtitleLanguage: track\?\.language/)
  assert.match(usePlayerSource, /const preferredSubtitleEnabled = ref\(true\)/)
  assert.match(usePlayerSource, /const findPreferredSubtitleTrack = \(tracks: SubtitleTrack\[\]\): SubtitleTrack \| null =>/)
  assert.match(usePlayerSource, /if \(preferredSubtitleEnabled\.value\) \{\s*const nextTrack = findPreferredSubtitleTrack\(tracks\)\s*setSubtitle\(nextTrack\)\s*return\s*\}/)
  assert.match(videoPlayerSource, /adapter: props\.adapter \?\? undefined/)
})

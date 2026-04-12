import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('widescreen toggle exits fullscreen before applying page theater mode', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /const toggleWidescreen = async \(\) => \{/)
  assert.match(source, /const nextWidescreen = !props\.widescreen/)
  assert.match(source, /pendingWidescreenValue\.value = nextWidescreen/)
  assert.match(source, /if \(isFullscreen\.value\) \{[\s\S]*?await toggleFullscreen\(\)[\s\S]*?return[\s\S]*?\}/)
  assert.match(source, /if \(pendingWidescreenValue\.value !== null && typeof document !== 'undefined' && !document\.fullscreenElement\)/)
  assert.match(source, /const resolvedWidescreen = pendingWidescreenValue\.value/)
  assert.match(source, /watch\(isFullscreen, \(fullscreen\) => \{/)
  assert.match(source, /if \(fullscreen \|\| pendingWidescreenValue\.value === null\) return/)
  assert.match(source, /emit\('widescreenChange', nextWidescreen\)/)
})

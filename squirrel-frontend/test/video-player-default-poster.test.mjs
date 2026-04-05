import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player does not render the built-in poster fallback overlay anymore', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.doesNotMatch(source, /class="sp-poster-fallback"/)
  assert.doesNotMatch(source, /SIGNAL_LOST/)
  assert.doesNotMatch(source, /READY_TO_DECODE/)
  assert.doesNotMatch(source, /\.sp-poster-fallback\s*\{/)
})

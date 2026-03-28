import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player toggles playback from the video surface instead of the root container', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')
  const rootTag = source.match(/<div[\s\S]*?class="sp-player"[\s\S]*?>/)

  assert.match(source, /<video[\s\S]*?@click="handleVideoClick"/)
  assert.ok(rootTag, 'expected to find the player root tag')
  assert.doesNotMatch(rootTag[0], /@click="handleVideoClick"/)
})

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player reuses the shared time formatter so hour-long videos render as h:mm:ss', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /import\s+\{\s*formatTime\s*\}\s+from\s+'@\/utils\/dateFormat'/)
  assert.doesNotMatch(source, /const formatTime = \(s: number\) => \{/)
})

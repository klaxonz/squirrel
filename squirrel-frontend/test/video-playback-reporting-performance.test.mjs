import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const reportingPath = new URL('../src/composables/usePlaybackReporting.ts', import.meta.url)
const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)

test('playback reporting keeps high-frequency time updates out of the reactive video snapshot', async () => {
  const source = await readFile(reportingPath, 'utf8')

  assert.doesNotMatch(source, /videoRef\.value\.last_position = currentTime/)
  assert.doesNotMatch(source, /videoRef\.value\.progress =/)
  assert.match(source, /const syncLocalPlaybackPosition = \(currentTime = lastObservedTime\) => \{/)
  assert.match(source, /const onVideoPause = \(\) => \{[\s\S]*syncLocalPlaybackPosition\(\)/)
})

test('video play global session bridge no longer deep-watches the entire video detail object', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.doesNotMatch(source, /watch\([\s\S]*\{ immediate: true, deep: true \}\s*\);/s)
  assert.match(source, /watch\([\s\S]*\{ immediate: true \}\s*\);/s)
})

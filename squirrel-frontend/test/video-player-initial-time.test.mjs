import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player applies initial time after source changes and metadata is ready', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /const applyInitialTime = \(source: MediaSource \| null \| undefined, time: number \| undefined\): void =>/)
  assert.match(source, /video\.addEventListener\('loadedmetadata', onLoadedMetadata, \{ once: true \}\)/)
  assert.match(source, /watch\(\(\) => props\.source, \(s, previousSource\) =>/)
  assert.match(source, /applyInitialTime\(s, props\.initialTime\)/)
})

test('video player does not reapply initial time after playback has already started', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /if \(store\.hasStartedPlayback \|\| currentTime\.value > 0\.5\) return/)
  assert.match(source, /watch\(\(\) => props\.initialTime, \(initialTime\) => \{/)
  assert.match(source, /applyInitialTime\(props\.source, initialTime\)/)
})

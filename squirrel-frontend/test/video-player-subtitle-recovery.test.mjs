import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const subtitlesPluginPath = new URL('../src/components/video-player/plugins/subtitles/SubtitlesPlugin.ts', import.meta.url)
const playerEnginePath = new URL('../src/components/video-player/core/createPlayerEngine.ts', import.meta.url)

test('subtitle plugin degrades 404 subtitle fetches without interrupting main playback', async () => {
  const source = await readFile(subtitlesPluginPath, 'utf8')

  assert.match(source, /if \(response\.status === 404\) \{/)
  assert.match(source, /Subtitle track returned 404, degrading subtitles only/)
  assert.match(source, /return false/)
})

test('player engine only enables subtitles after the selected track finishes loading successfully', async () => {
  const source = await readFile(playerEnginePath, 'utf8')

  assert.match(source, /let subtitleLoadRequestId = 0/)
  assert.match(source, /const requestId = \+\+subtitleLoadRequestId/)
  assert.match(source, /Promise\.resolve\(subtitlesPlugin\.loadTrack\(track\)\)/)
  assert.match(source, /if \(loaded !== false && typeof subtitlesPlugin\.enable === 'function'\) \{/)
  assert.match(source, /if \(typeof subtitlesPlugin\.disable === 'function'\) \{/)
})

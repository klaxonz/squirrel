import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const playbackProvidersPath = new URL('../src/playback/providers/index.mjs', import.meta.url)

test('desktop playback prewarm registry only includes youtube', async () => {
  const source = await readFile(playbackProvidersPath, 'utf8')

  assert.match(source, /import \{ prewarmYouTubePlayback \}/)
  assert.match(source, /\{ name: 'youtube', prewarm: prewarmYouTubePlayback \}/)
  assert.doesNotMatch(source, /javdb|prewarmJavdbCloudflare|pornhub|youporn/)
})

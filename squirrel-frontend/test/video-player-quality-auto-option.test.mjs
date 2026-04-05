import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const playerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player renders an explicit auto option in the quality menu', async () => {
  const source = await readFile(playerPath, 'utf8')

  assert.match(source, /handleAutoQualitySelect/)
  assert.match(source, /settingsView === 'quality'[\s\S]*handleAutoQualitySelect\(\)/)
  assert.match(source, /currentQualityId === null/)
  assert.match(source, />\s*AUTO\s*</)
})

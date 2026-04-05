import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const playerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player does not render a frontend-only auto option in the quality menus', async () => {
  const source = await readFile(playerPath, 'utf8')

  assert.doesNotMatch(source, /handleAutoQualitySelect/)
  assert.doesNotMatch(source, /settingsView === 'quality'[\s\S]*currentQualityId === null[\s\S]*AUTO/)
  assert.doesNotMatch(source, /v-if="showQualityMenu"[\s\S]*currentQualityId === null[\s\S]*AUTO/)
  assert.doesNotMatch(source, /currentQualityLabel \|\| 'AUTO'/)
})

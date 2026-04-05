import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player uses a dedicated quality popover without a back action for the standalone quality trigger', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')
  const qualityPopover = source.match(/<div v-if="showQualityMenu"[\s\S]*?<\/div>\s*<\/transition>/)

  assert.match(source, /@click\.stop="toggleQualityMenu"/)
  assert.match(source, /const showQualityMenu = ref\(false\)/)
  assert.ok(qualityPopover, 'expected to find the standalone quality popover')
  assert.match(qualityPopover[0], /v-for="q in displayedQualities"/)
  assert.doesNotMatch(qualityPopover[0], />\s*AUTO\s*</)
  assert.doesNotMatch(qualityPopover[0], /chevronLeft/)
  assert.doesNotMatch(qualityPopover[0], /settingsView = 'main'/)
})

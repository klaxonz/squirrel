import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)

test('video player uses a dedicated quality popover without a back action for the standalone quality trigger', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')
  const qualityPopover = source.match(/<div v-if="showQualityMenu"[\s\S]*?<\/div>\s*<\/transition>/)

  assert.match(source, /@click\.stop="toggleQualityMenu"/)
  assert.match(source, /const showQualityMenu = ref\(false\)/)
  assert.match(source, /class="sp-quality-tag"[\s\S]*:class="\{ 'is-active': showQualityMenu \}"/)
  assert.match(source, /\.sp-quality-tag:hover,\s*\.sp-quality-tag\.is-active\s*\{/)
  assert.match(source, /\.sp-quality-tag\s*\{[^}]*color:\s*rgba\(255,\s*255,\s*255,\s*0\.7\);/s)
  assert.match(source, /\.sp-quality-tag\s*\{[^}]*border:\s*1px solid transparent;/s)
  assert.match(source, /\.sp-quality-tag:hover,\s*\.sp-quality-tag\.is-active\s*\{[^}]*color:\s*var\(--sp-primary,\s*#ff4d00\);/s)
  assert.match(source, /\.sp-quality-tag:hover,\s*\.sp-quality-tag\.is-active\s*\{[^}]*border-color:\s*var\(--sp-border\);/s)
  assert.match(source, /\.sp-quality-tag:hover,\s*\.sp-quality-tag\.is-active\s*\{[^}]*background:\s*var\(--sp-bg-hover\);/s)
  assert.ok(qualityPopover, 'expected to find the standalone quality popover')
  assert.match(qualityPopover[0], /v-for="q in displayedQualities"/)
  assert.doesNotMatch(qualityPopover[0], />\s*AUTO\s*</)
  assert.doesNotMatch(qualityPopover[0], /chevronLeft/)
  assert.doesNotMatch(qualityPopover[0], /settingsView = 'main'/)
})

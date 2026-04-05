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

test('video player hides the floating quality tag when the runtime label is only an internal level token', async () => {
  const source = await readFile(playerPath, 'utf8')

  assert.match(source, /const isInternalQualityLabel = \(label: string \| null \| undefined\) => \/\^level\[_\\s-\]\?\\d\+\$\/i\.test\(String\(label \|\| ''\)\.trim\(\)\)/)
  assert.match(source, /const isAutoQualityLabel = \(label: string \| null \| undefined\) => \['auto', '自动', '自動'\]\.includes\(String\(label \|\| ''\)\.trim\(\)\.toLowerCase\(\)\)/)
  assert.match(source, /const isDisplayableQualityLabel = \(label: string \| null \| undefined\) => !isInternalQualityLabel\(label\) && !isAutoQualityLabel\(label\)/)
  assert.match(source, /const currentQualityTagLabel = computed\(\(\) => \([\s\S]*?isDisplayableQualityLabel\(currentQualityLabel\.value\) \? \(currentQualityLabel\.value \|\| ''\) : ''[\s\S]*?\)\)/)
  assert.match(source, /const qualityMenuLabel = computed\(\(\) => isDisplayableQualityLabel\(currentQualityLabel\.value\) \? \(currentQualityLabel\.value \|\| ''\) : \(displayedQualities\.value\[0\]\?\.label \|\| t\('quality'\)\)\)/)
  assert.match(source, /<div v-if="displayedQualities\.length > 0 && currentQualityTagLabel" class="sp-quality-tag" @click\.stop="toggleQualityMenu">/)
  assert.doesNotMatch(source, /<div v-if="displayedQualities\.length > 0" class="sp-quality-tag" @click\.stop="toggleQualityMenu">/)
})

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const useVideoOperationsPath = new URL('../src/composables/useVideoOperations.ts', import.meta.url)
const dashPluginPath = new URL('../src/components/video-player/plugins/dash/DashPlugin.ts', import.meta.url)

test('video operations forward backend quality hints into the player source', async () => {
  const source = await readFile(useVideoOperationsPath, 'utf8')

  assert.match(source, /const qualities = \(data\?\.qualities \|\| \[\]\)\.map\(/)
  assert.match(source, /codec:\s*item\.codec/)
})

test('dash plugin maps backend quality hints onto dash tracks before switching quality', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /getTracksFor\?\.\('video'\)/)
  assert.match(source, /setCurrentTrack\(targetTrack\)/)
  assert.match(source, /setQualityFor\('video',\s*hintedSelection\.qualityIndex,\s*true\)/)
})

test('dash plugin waits for track rendering before applying a quality index on another track', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /pendingHintedSelection/)
  assert.match(source, /trackChangeRendered/)
  assert.match(source, /pendingHintedSelection\.trackIndex === this\.currentTrackIndex/)
})

test('dash plugin flushes buffered video after cross-track switches', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /flushBufferAtTrackSwitch:\s*true/)
})

test('dash plugin limits the visible quality menu to the selected codec family', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /const visibleCodecFamily = this\.resolveVisibleCodecFamily\(\)/)
  assert.match(source, /this\.getCodecFamily\(hint\.codec\) === visibleCodecFamily/)
})

test('dash plugin prefers the active codec family for the quality menu before falling back to a speculative codec ladder', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /const activeCodecFamily = this\.getActiveCodecFamily\(\)/)
  assert.match(source, /if \(activeCodecFamily && availableFamilies\.includes\(activeCodecFamily\)\)/)
  assert.match(source, /return activeCodecFamily/)
})

test('dash plugin refreshes visible qualities after the active track becomes known', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /player\.on\('qualityChangeRendered'[\s\S]{0,900}this\.updateQualities\(\)/)
  assert.match(source, /player\.on\('trackChangeRendered'[\s\S]{0,900}this\.updateQualities\(\)/)
})

test('dash plugin keeps codec family as an explicit selection state', async () => {
  const source = await readFile(dashPluginPath, 'utf8')

  assert.match(source, /private selectedCodecFamily:\s*string\s*=\s*'auto'/)
  assert.match(source, /getAvailableCodecFamilies\(\):\s*string\[\]/)
  assert.match(source, /getSelectedCodecFamily\(\):\s*string/)
  assert.match(source, /setCodecFamily\(codecFamily:\s*string\):\s*void/)
  assert.match(source, /const visibleCodecFamily = this\.resolveVisibleCodecFamily\(\)/)
})

test('player runtime exposes codec families and codec switching controls', async () => {
  const source = await readFile(new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url), 'utf8')

  assert.match(source, /const codecFamilies = ref<string\[\]>\(\[\]\)/)
  assert.match(source, /const selectedCodecFamily = ref<string>\('auto'\)/)
  assert.match(source, /const currentCodecFamily = ref<string \| null>\(null\)/)
  assert.match(source, /const setCodecFamily = \(codecFamily: string\): void =>/)
  assert.match(source, /codecFamilies,/)
  assert.match(source, /selectedCodecFamily,/)
  assert.match(source, /currentCodecFamily,/)
  assert.match(source, /setCodecFamily,/)
})

test('video player renders a dedicated codec menu alongside the quality menu', async () => {
  const source = await readFile(new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url), 'utf8')

  assert.match(source, /v-if="codecFamilies\.length > 1"/)
  assert.match(source, /settingsView = 'codec'/)
  assert.match(source, /v-else-if="settingsView === 'codec'"/)
  assert.match(source, /handleCodecFamilySelect/)
  assert.doesNotMatch(source, /handleCodecFamilySelect\('auto'\)/)
  assert.doesNotMatch(source, /selectedCodecFamily === 'auto'/)
  assert.doesNotMatch(source, /codecAutoLabel/)
})

test('video player filters the quality menu by the selected or active codec family', async () => {
  const source = await readFile(new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url), 'utf8')

  assert.match(source, /const visibleCodecFamily = computed\(\(\) =>/)
  assert.doesNotMatch(source, /inferCodecFamilyFromLabel\(currentQualityLabel\.value\)/)
  assert.match(source, /selectedCodecFamily\.value !== 'auto'/)
  assert.match(source, /:\s*currentCodecFamily\.value/)
  assert.match(source, /const displayedQualities = computed\(\(\) =>/)
  assert.match(source, /qualities\.value\.filter\(\(quality\) => getCodecFamily\(quality\.codec\) === visibleCodecFamily\.value\)/)
  assert.match(source, /v-for="q in displayedQualities"/)
})

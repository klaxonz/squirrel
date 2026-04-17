import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)
const orchestratorPath = new URL('../src/composables/usePlaybackOrchestrator.ts', import.meta.url)
const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)
const globalPlayerHostPath = new URL('../src/components/video-player/GlobalVideoPlayerHost.vue', import.meta.url)

test('playback orchestrator exposes a page-level playback resolving state and starts source resolution before waiting for detail hydration', async () => {
  const source = await readFile(orchestratorPath, 'utf8')

  assert.match(source, /const isResolvingPlayback = ref\(false\)/)
  assert.match(source, /isResolvingPlayback\.value = true/)
  assert.match(source, /const playbackPromise = getPlaybackSource\(videoId, options\)/)
  assert.match(source, /const detailPromise = !hasInitialData/)
  assert.match(source, /const source = await playbackPromise/)
  assert.match(source, /if \(seq === requestSeq\.value\) \{\s*isResolvingPlayback\.value = false\s*\}/)
  assert.match(source, /isResolvingPlayback,/)
})

test('video play forwards playback resolution state into the player instead of rendering its own overlay', async () => {
  const source = await readFile(videoPlayPath, 'utf8')
  const hostSource = await readFile(globalPlayerHostPath, 'utf8')

  assert.match(source, /v-if="video \|\| playbackSource \|\| isResolvingPlayback \|\| externalError"/)
  assert.match(source, /isResolvingPlayback/)
  assert.match(source, /externalLoading: nextExternalLoading/)
  assert.match(source, /externalLoadingText: '正在建立播放链路'/)
  assert.match(hostSource, /:external-loading="globalVideoPlayerSession\.externalLoading"/)
  assert.match(hostSource, /:external-loading-text="globalVideoPlayerSession\.externalLoadingText"/)
  assert.doesNotMatch(source, /class="video-stage-loading"/)
})

test('video player reuses its built-in loading layer for external playback resolution states', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /externalLoading\?: boolean/)
  assert.match(source, /externalLoadingText\?: string/)
  assert.match(source, /const showLoadingOverlay = computed\(\(\) => \(store\.loading \|\| props\.externalLoading\) && !errorState\.value\.show\)/)
  assert.match(source, /v-if="showLoadingOverlay"/)
  assert.match(source, /v-if="props\.externalLoadingText"/)
})

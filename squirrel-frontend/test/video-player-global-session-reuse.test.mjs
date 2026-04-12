import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const sessionPath = new URL('../src/composables/useGlobalVideoPlayer.js', import.meta.url)
const orchestratorPath = new URL('../src/composables/usePlaybackOrchestrator.ts', import.meta.url)
const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)

test('global player session keeps the video snapshot and related rail data for route restoration', async () => {
  const source = await readFile(sessionPath, 'utf8')

  assert.match(source, /videoSnapshot:\s*null/)
  assert.match(source, /relatedVideos:\s*\[\]/)
  assert.match(source, /loadingRelated:\s*false/)
})

test('playback orchestrator can hydrate page state from an existing global session without refetching playback', async () => {
  const source = await readFile(orchestratorPath, 'utf8')

  assert.match(source, /const hydratePlaybackState = \(\{/)
  assert.match(source, /setVideoSnapshot\(videoSnapshot\)/)
  assert.match(source, /playbackSource\.value = nextPlaybackSource/)
  assert.match(source, /setRelatedVideosSnapshot\(nextRelatedVideos as any\[\], nextLoadingRelated\)/)
})

test('video play reuses the active global playback session before calling loadAndPlayById again', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /const hasReusableGlobalPlaybackSession = \(videoId = route\.params\.videoId\) => \{/)
  assert.match(source, /const hydrateFromGlobalPlaybackSession = \(\) => \{/)
  assert.match(source, /if \(hasReusableGlobalPlaybackSession\(\)\) \{\s*hydrateFromGlobalPlaybackSession\(\);\s*\} else \{\s*await loadAndPlayById\(route\.params\.videoId\);/s)
  assert.match(source, /if \(hasReusableGlobalPlaybackSession\(newId\)\) \{\s*hydrateFromGlobalPlaybackSession\(\);\s*\} else \{\s*await loadAndPlayById\(newId\);/s)
  assert.match(source, /if \(!hasLocalPlaybackState && hasReusableGlobalPlaybackSession\(\)\) \{\s*return;\s*\}/s)
})

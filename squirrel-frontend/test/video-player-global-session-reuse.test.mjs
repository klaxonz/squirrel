import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const sessionPath = new URL('../src/composables/useGlobalVideoPlayer.js', import.meta.url)
const orchestratorPath = new URL('../src/composables/usePlaybackOrchestrator.ts', import.meta.url)
const shellPath = new URL('../src/composables/useVideoPlaybackShell.ts', import.meta.url)
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
  const shellSource = await readFile(shellPath, 'utf8')
  const videoPlaySource = await readFile(videoPlayPath, 'utf8')

  assert.match(shellSource, /const hasReusableGlobalPlaybackSession = \(videoId = route\.params\.videoId\) => \{/)
  assert.match(shellSource, /const hydrateFromGlobalPlaybackSession = \(\) => \{/)
  assert.doesNotMatch(shellSource, /watch\(\(\) => route\.params\.videoId, \(videoId\) => \{\s*setGlobalVideoPlayerCurrentVideoId\(videoId\);/s)
  assert.match(videoPlaySource, /watch\(\(\) => route\.params\.videoId, \(videoId\) => \{\s*setCurrentVideo\(videoId \?\? null\);/s)
  assert.match(shellSource, /currentVideoId: String\(nextVideo\?\.id \?\? route\.params\.videoId \?\? ''\)/)
  assert.match(shellSource, /if \(hasReusableGlobalPlaybackSession\(\)\) \{\s*hydrateFromGlobalPlaybackSession\(\)\s*\} else \{\s*await loadAndPlayById\(route\.params\.videoId, consumePlaybackSeed\(route\.params\.videoId\)\)/s)
  assert.match(shellSource, /if \(hasReusableGlobalPlaybackSession\(newId\)\) \{\s*hydrateFromGlobalPlaybackSession\(\)\s*\} else \{\s*await loadAndPlayById\(newId, consumePlaybackSeed\(newId\)\)/s)
  assert.match(shellSource, /if \(!hasLocalPlaybackState && hasReusableGlobalPlaybackSession\(\)\) \{\s*return\s*\}/s)
})

test('video play does not treat a snapshot-only global session as reusable playback state', async () => {
  const source = await readFile(shellPath, 'utf8')
  const reusableSessionMatch = source.match(/const hasReusableGlobalPlaybackSession = \([\s\S]*?\n  }\n/)

  assert.ok(reusableSessionMatch)
  assert.match(source, /globalVideoPlayerSession\.source/)
  assert.match(source, /globalVideoPlayerSession\.externalError/)
  assert.match(source, /globalVideoPlayerSession\.externalLoading/)
  assert.doesNotMatch(reusableSessionMatch[0], /globalVideoPlayerSession\.videoSnapshot/)
})

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const useVideoOperationsPath = new URL('../src/composables/useVideoOperations.ts', import.meta.url)
const useVideoDetailPath = new URL('../src/composables/useVideoDetail.ts', import.meta.url)
const usePlaybackOrchestratorPath = new URL('../src/composables/usePlaybackOrchestrator.ts', import.meta.url)
const hlsPluginPath = new URL('../src/components/video-player/plugins/hls/HlsPlugin.ts', import.meta.url)

test('video operations synthesize an mpd fallback when backend returns split audio and video streams', async () => {
  const source = await readFile(useVideoOperationsPath, 'utf8')

  assert.match(source, /const synthesizedMpdUrl = videoUrl && audioUrl && !mpdUrl\s*\?\s*`\/api\/video\/mpd\?video_id=\$\{encodeURIComponent\(String\(videoId\)\)\}`\s*:\s*undefined/)
  assert.match(source, /const resolvedMpdUrl = mpdUrl \|\| synthesizedMpdUrl/)
  assert.match(source, /if \(resolvedMpdUrl\) return \{ src: resolvedMpdUrl, type: 'auto', key, progressKey, qualities \}/)
})

test('video detail ignores stale detail responses after a newer request or snapshot update wins', async () => {
  const source = await readFile(useVideoDetailPath, 'utf8')

  assert.match(source, /let detailRequestSeq = 0/)
  assert.match(source, /const setVideoSnapshot = \(nextVideo: VideoLike \| null\) =>/)
  assert.match(source, /const seq = \+\+detailRequestSeq/)
  assert.match(source, /if \(!error && seq === detailRequestSeq\) \{\s*replaceVideo\(data \|\| null\)\s*\}/)
})

test('video detail revokes generated subtitle object urls when replacing the active video or disposing the composable', async () => {
  const source = await readFile(useVideoDetailPath, 'utf8')

  assert.match(source, /const managedSubtitleObjectUrls = new Set<string>\(\)/)
  assert.match(source, /URL\.revokeObjectURL\(url\)/)
  assert.match(source, /onScopeDispose\(\(\) => \{\s*revokeManagedSubtitleObjectUrls\(\)\s*\}\)/)
  assert.match(source, /managedSubtitleObjectUrls\.add\(objectUrl\)/)
})

test('playback orchestrator invalidates stale detail writes before seeding a new snapshot', async () => {
  const source = await readFile(usePlaybackOrchestratorPath, 'utf8')

  assert.match(source, /const \{ video, startTime, fetchVideoDetails, maybeInjectSubtitles, setVideoSnapshot \} = useVideoDetail\(initialVideo\)/)
  assert.match(source, /setVideoSnapshot\(initialVideoData as any\)/)
  assert.doesNotMatch(source, /video\.value = initialVideoData as any/)
})

test('hls plugin clears scheduled retry timers when sources change or the plugin is destroyed', async () => {
  const source = await readFile(hlsPluginPath, 'utf8')

  assert.match(source, /private retryTimer: ReturnType<typeof setTimeout> \| null = null/)
  assert.match(source, /private reloadTimer: ReturnType<typeof setTimeout> \| null = null/)
  assert.match(source, /this\.retryTimer = setTimeout\(/)
  assert.match(source, /this\.reloadTimer = setTimeout\(/)
  assert.match(source, /clearTimeout\(this\.retryTimer\)/)
  assert.match(source, /clearTimeout\(this\.reloadTimer\)/)
})

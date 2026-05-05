import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const useVideoOperationsPath = new URL('../src/composables/useVideoOperations.ts', import.meta.url)
const useVideoDetailPath = new URL('../src/composables/useVideoDetail.ts', import.meta.url)
const usePlaybackOrchestratorPath = new URL('../src/composables/usePlaybackOrchestrator.ts', import.meta.url)
const hlsPluginPath = new URL('../src/components/video-player/plugins/hls/HlsPlugin.ts', import.meta.url)
const subtitlesPluginPath = new URL('../src/components/video-player/plugins/subtitles/SubtitlesPlugin.ts', import.meta.url)
const videoPlayerPath = new URL('../src/components/video-player/VideoPlayer.vue', import.meta.url)
const usePlayerPath = new URL('../src/components/video-player/runtime/usePlayer.ts', import.meta.url)

test('video operations synthesize an mpd fallback when backend returns split audio and video streams', async () => {
  const source = await readFile(useVideoOperationsPath, 'utf8')

  assert.match(source, /if \(typeof window === 'undefined'\) return false/)
  assert.match(source, /if \(desktopWindow\.desktopApp\?\.isDesktop === true\) return true/)
  assert.match(source, /return \/electron\|tauri\/i\.test\(userAgent\)/)
  assert.doesNotMatch(source, /userAgentData\?\.mobile === false/)
  assert.doesNotMatch(source, /linux x86_64|macintosh|windows nt|cros/)
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

  assert.doesNotMatch(source, /const managedSubtitleObjectUrls = new Set<string>\(\)/)
  assert.doesNotMatch(source, /URL\.revokeObjectURL\(url\)/)
  assert.doesNotMatch(source, /Blob\(\[data\]/)
  assert.match(source, /const subtitlePlaceholders = candidates/)
  assert.match(source, /url: `\/api\/video\/subtitles\?\$\{params\.toString\(\)\}`/)
})

test('video detail builds lazy subtitle endpoints through per-site candidate lists instead of prefetching subtitle bodies', async () => {
  const source = await readFile(useVideoDetailPath, 'utf8')

  assert.match(source, /pattern: \/bilibili\\\.com\/i/)
  assert.match(source, /pattern: \/\(\?:youtube\\\.com\|youtu\\\.be\)\/i/)
  assert.match(source, /\{ id: 'yt-en', language: '英语', lang: 'en' \}/)
  assert.match(source, /\{ id: 'yt-en-US', language: '美式英语', lang: 'en-US' \}/)
  assert.match(source, /\{ id: 'yt-default', language: '默认' \}/)
  assert.match(source, /const candidates = getSubtitleCandidates\(snapshot\.url\)/)
  assert.match(source, /const params = new URLSearchParams\(\{\s*video_id: String\(videoId\),\s*fmt: 'srt',\s*\}\)/)
  assert.match(source, /if \(candidate\.lang\) \{\s*params\.set\('lang', candidate\.lang\)\s*\}/)
  assert.doesNotMatch(source, /getVideoSubtitles\(videoId, \{ lang: candidate\.lang, fmt: 'srt' \}\)/)
  assert.doesNotMatch(source, /if \(!url \|\| !\/bilibili\\\.com\/\.test\(url\)\) return/)
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

test('subtitle plugin clears active subtitle state when tracks disappear', async () => {
  const source = await readFile(subtitlesPluginPath, 'utf8')

  assert.match(source, /if \(tracks\.length === 0\) \{/)
  assert.match(source, /this\.currentTrack = null/)
  assert.match(source, /this\.cues = \[\]/)
  assert.match(source, /this\.disable\(\)/)
})

test('subtitle plugin refreshes the current cue as soon as a track finishes loading or subtitles are re-enabled', async () => {
  const source = await readFile(subtitlesPluginPath, 'utf8')

  assert.match(source, /private clearRenderedCue\(\): void \{/)
  assert.match(source, /private refreshCurrentCue\(\): void \{/)
  assert.match(source, /const currentTime = this\.context\?\.videoElement\?\.currentTime \?\? this\.context\?\.state\.currentTime \?\? 0/)
  assert.match(source, /this\.clearRenderedCue\(\)/)
  assert.match(source, /if \(this\.enabled\) \{\s*this\.refreshCurrentCue\(\)\s*\}/)
  assert.match(source, /enable\(\): void \{[\s\S]*this\.refreshCurrentCue\(\)/)
})

test('player runtime keeps subtitle selection state aligned with incoming tracks without auto-enabling fresh subtitle lists', async () => {
  const source = await readFile(usePlayerPath, 'utf8')

  assert.match(source, /const nextTrack = tracks\.find\(\(track\) => track\.id === currentSubtitle\.value\?\.id\)/)
  assert.match(source, /store\.setCurrentSubtitle\(nextTrack\)/)
  assert.match(source, /if \(nextTrack && store\.subtitlesEnabled\) \{\s*engine\.setSubtitle\(nextTrack\)/)
  assert.match(source, /store\.setSubtitlesEnabled\(false\)/)
  assert.match(source, /engine\.setSubtitle\(null\)/)
  assert.match(source, /if \(subtitleTracks\.value\.length > 0\) \{\s*await setSubtitleTracks\(subtitleTracks\.value\)\s*\}/)
})

test('subtitle plugin caches fetched subtitle bodies after the first lazy load', async () => {
  const source = await readFile(subtitlesPluginPath, 'utf8')

  assert.match(source, /if \(!content && track\.url\) \{/)
  assert.match(source, /const response = await fetch\(track\.url\)/)
  assert.match(source, /track\.content = content/)
})

test('video player exposes subtitle settings alongside quick toggle controls', async () => {
  const source = await readFile(videoPlayerPath, 'utf8')

  assert.match(source, /settingsView === 'subtitles'/)
  assert.match(source, /{{ t\('subtitleSettings'\) }}/)
  assert.match(source, /handleSubtitleSelect\(track\)/)
  assert.match(source, /handleSubtitleDisable/)
  assert.match(source, /const subtitleMenuLabel = computed\(\(\) => \{/)
})

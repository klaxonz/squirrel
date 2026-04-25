import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const navigationPath = new URL('../src/composables/useVideoPageNavigation.ts', import.meta.url)
const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)
const shellPath = new URL('../src/composables/useVideoPlaybackShell.ts', import.meta.url)
const latestVideosPath = new URL('../src/views/LatestVideos.vue', import.meta.url)
const historyPath = new URL('../src/views/History.vue', import.meta.url)
const playlistViewPath = new URL('../src/views/PlaylistView.vue', import.meta.url)
const subscribedPath = new URL('../src/views/Subscribed.vue', import.meta.url)

test('video navigation remembers playback seed data before routing to the playback page', async () => {
  const source = await readFile(navigationPath, 'utf8')

  assert.match(source, /import \{ rememberVideoPlaybackSeed \} from '\.\/videoPlaybackSeed'/)
  assert.match(source, /if \(videoData\) \{\s*rememberVideoPlaybackSeed\(videoData\)\s*\}/)
})

test('video play consumes remembered playback seed data on initial entry and route switches', async () => {
  const videoPlaySource = await readFile(videoPlayPath, 'utf8')
  const shellSource = await readFile(shellPath, 'utf8')

  assert.match(videoPlaySource, /import \{ consumeVideoPlaybackSeed, peekVideoPlaybackSeed \} from '@\/composables\/videoPlaybackSeed'/)
  assert.match(videoPlaySource, /const getRoutePlaybackSeed = \(videoId = route\.params\.videoId\) => consumeVideoPlaybackSeed\(videoId\)/)
  assert.match(videoPlaySource, /const initialPlaybackSeed = peekVideoPlaybackSeed\(route\.params\.videoId\)/)
  assert.match(videoPlaySource, /usePlaybackOrchestrator\(initialPlaybackSeed\)/)
  assert.match(shellSource, /await loadAndPlayById\(route\.params\.videoId, consumePlaybackSeed\(route\.params\.videoId\)\)/)
  assert.match(shellSource, /await loadAndPlayById\(newId, consumePlaybackSeed\(newId\)\)/)
})

test('latest videos remembers playback seed data before pushing into the video route', async () => {
  const source = await readFile(latestVideosPath, 'utf8')

  assert.match(source, /import \{ rememberVideoPlaybackSeed \} from '@\/composables\/videoPlaybackSeed'/)
  assert.match(source, /const handleOpenModal = \(video\) => \{\s*rememberVideoPlaybackSeed\(video\)\s*router\.push\(`\/video\/\$\{video\.id\}`\)\s*\}/)
})

test('history and playlist entry points remember playback seed data before pushing into the video route', async () => {
  const historySource = await readFile(historyPath, 'utf8')
  const playlistSource = await readFile(playlistViewPath, 'utf8')

  assert.match(historySource, /import \{ rememberVideoPlaybackSeed \} from '@\/composables\/videoPlaybackSeed'/)
  assert.match(historySource, /const handleOpenModal = \(video\) => \{\s*rememberVideoPlaybackSeed\(video\);\s*router\.push\(`\/video\/\$\{video\.id\}`\);?\s*\}/)
  assert.match(playlistSource, /import \{ rememberVideoPlaybackSeed \} from '@\/composables\/videoPlaybackSeed'/)
  assert.match(playlistSource, /rememberVideoPlaybackSeed\(item\.video\)/)
})

test('subscribed recent videos remember playback seed data before opening the player page', async () => {
  const source = await readFile(subscribedPath, 'utf8')

  assert.match(source, /import \{ rememberVideoPlaybackSeed \} from '@\/composables\/videoPlaybackSeed'/)
  assert.match(source, /@click\.stop="openRecentVideo\(video\)"/)
  assert.match(source, /const openRecentVideo = \(video\) => \{\s*const videoId = video\?\.id\s*if \(!videoId\) return\s*rememberVideoPlaybackSeed\(video\)\s*router\.push\(`\/video\/\$\{videoId\}`\)\s*\}/)
})

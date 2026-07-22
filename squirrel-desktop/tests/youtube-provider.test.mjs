import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const providerPath = new URL('../src/playback/providers/youtube/index.mjs', import.meta.url)
const corePath = new URL('../src/playback/providers/youtube/youtubei_core.mjs', import.meta.url)
const mainPath = new URL('../src/main.mjs', import.meta.url)
const siteLoginPath = new URL('../src/site-login.mjs', import.meta.url)
const ipcHandlersPath = new URL('../src/ipc-handlers.mjs', import.meta.url)
const ipcPlaybackPath = new URL('../src/ipc-playback.mjs', import.meta.url)
const pluginCorePath = new URL('../../squirrel-site-runtimes/youtube/src/squirrel_youtube/node/youtubei_core.mjs', import.meta.url)
const frontendDetailPath = new URL('../renderer/src/features/video/composables/useVideoDetail.ts', import.meta.url)

test('desktop youtube provider keeps complete dash payload for direct playback', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /resolveYoutubeiPayload\(\{[\s\S]*?resolution_mode:\s*'all'/)
  assert.doesNotMatch(source, /include_local_dash_manifest:\s*false/)
  assert.match(source, /const PLAYBACK_CACHE_VERSION = 'mweb-pot-v1'/)
  assert.match(source, /const cacheKey = `\$\{PLAYBACK_CACHE_VERSION\}\|\$\{videoId\}/)
})

test('desktop youtube playback uses official youtubei.js toDash only', async () => {
  const source = await readFile(providerPath, 'utf8')
  const coreSource = await readFile(corePath, 'utf8')

  // No homemade MPD builders / media proxy.
  assert.doesNotMatch(source, /buildFallbackLocalDashManifest/)
  assert.doesNotMatch(source, /buildRepresentationXml/)
  assert.doesNotMatch(source, /buildSegmentBaseXml/)
  assert.doesNotMatch(source, /representationGroupKey/)
  assert.doesNotMatch(source, /rewriteYouTubeMpdThroughProxy/)
  assert.doesNotMatch(source, /youtube-media-proxy/)

  // Official path: VideoInfo.toDash, then YouTube-hosted dash_manifest_url.
  assert.match(source, /VideoInfo\.toDash\(\)/)
  assert.match(source, /streaming_data\.dash_manifest_url/)
  assert.match(coreSource, /manifestInfo\.toDash\(/)
})

test('renderer youtube official dash uses FreeTube data URL + shaka', async () => {
  const opsPath = new URL(
    '../renderer/src/features/video/composables/useVideoOperations.ts',
    import.meta.url,
  )
  const shakaPath = new URL(
    '../renderer/src/features/playback/components/video-player/adapters/ShakaDashAdapter.ts',
    import.meta.url,
  )
  const opsSource = await readFile(opsPath, 'utf8')
  const shakaSource = await readFile(shakaPath, 'utf8')

  // FreeTube Watch.createLocalDashManifest style data: URL for official toDash body.
  assert.match(opsSource, /data:application\/dash\+xml;charset=UTF-8/)
  assert.match(opsSource, /playbackEngine:\s*'shaka'/)
  assert.match(opsSource, /isYouTubeOfficialDash/)

  // FreeTube googlevideo videoplayback filters (POST + alr + http-body redirect).
  assert.match(shakaSource, /installYouTubeNetworkingFilters/)
  assert.match(shakaSource, /alr=yes/)
  assert.match(shakaSource, /request\.method = 'POST'/)
  assert.match(shakaSource, /HTTP_IN_HEX/)
  // FreeTube getPlayerConfig buffer goals (not the old 10s/2s spinner-prone defaults).
  assert.match(shakaSource, /bufferingGoal:\s*180/)
  assert.match(shakaSource, /rebufferingGoal:\s*0\.02/)
  assert.match(shakaSource, /restrictToElementSize:\s*true/)

  // Seek/spinner: StreamSink loadingStateChanged must re-emit waiting/canplay so
  // usePlayer store.loading clears after Shaka rebuffer (not just engine flag).
  const enginePath = new URL(
    '../renderer/src/features/playback/components/video-player/core/createPlayerEngine.ts',
    import.meta.url,
  )
  const videoPlayerPath = new URL(
    '../renderer/src/features/playback/components/video-player/VideoPlayer.vue',
    import.meta.url,
  )
  const engineSource = await readFile(enginePath, 'utf8')
  const videoPlayerSource = await readFile(videoPlayerPath, 'utf8')
  assert.match(engineSource, /loadingStateChanged:\s*\(isLoading\)\s*=>\s*\{[\s\S]*?events\.emit\('waiting'/)
  assert.match(engineSource, /clearLoadingState\(/)
  // FreeTube: do not force spinner before every seek — stream-owned path only
  // waits when the landing is unbuffered; spinner primarily tracks isBuffering.
  assert.match(engineSource, /const seek = \(time: number\): void => \{[\s\S]*?streamOwned/)
  assert.match(engineSource, /resumeAfterSeek/)
  assert.match(engineSource, /const onPause = \(\) => \{[\s\S]*?resumeAfterSeek = false/)
  // FreeTube rebufferingGoal 0.02 — clear spinner with a few frames, not 0.5s+.
  assert.match(engineSource, /minAheadSec = 0\.05/)
  assert.match(shakaSource, /syncBufferingToSink/)
  // dash.js/Shaka own buffering state. HLS still relies on native canplay/waiting.
  assert.match(
    engineSource,
    /streamAdapterOwnsBuffering[\s\S]*?currentAdapterType === 'dash'[\s\S]*?currentAdapterType === 'shaka-dash'/,
  )
  assert.match(engineSource, /if \(streamAdapterOwnsBuffering\(\)\) return false/)
  // rate=0 starve flag must be restored before play() or A/V freeze after scrub.
  assert.match(engineSource, /ensurePlaybackRate/)
  assert.match(engineSource, /playbackRate === 0/)
  // DASH native waiting must not re-arm stall recovery over Shaka buffering.
  assert.match(
    engineSource,
    /const onWaiting = \(\) => \{[\s\S]*?streamAdapterOwnsBuffering\(\)[\s\S]*?return/,
  )
  // Visibility regain must NOT re-seek (aborts googlevideo segments mid-play).
  assert.doesNotMatch(
    videoPlayerSource,
    /handleVisibilityChange[\s\S]*?video\.currentTime\s*=\s*t/,
  )

  // Shaka buffering is FakeEvent.buffering (Map props), not CustomEvent.detail.
  assert.match(shakaSource, /typeof e\.buffering === 'boolean'/)
  assert.match(shakaSource, /isBuffering\(\)/)
  // Stall recovery must NOT re-seek the same time (aborts googlevideo segments).
  assert.match(shakaSource, /retryStreaming/)
  assert.match(shakaSource, /NEVER re-seek to the same time/)
  // Resume only when rate stuck at 0 (Shaka STARVING) — not every paused state.
  assert.match(shakaSource, /restorePlaybackRateAfterRebuffer/)
  assert.match(shakaSource, /playbackRate !== 0/)
  assert.match(shakaSource, /this\.player !== seekPlayer/)
  assert.match(shakaSource, /const shouldResume = Boolean\(video && !video\.paused && !video\.ended\)/)
  // FreeTube: literal string append — never URLSearchParams (re-encodes sig/lsig).
  // Idempotent: do not stack range/alr on Shaka retries of an already-rewritten URI.
  assert.match(shakaSource, /request\.uris\[0\] \+= `&range=\$\{/)
  assert.match(shakaSource, /request\.uris\[0\] \+= '&alr=yes'/)
  assert.match(shakaSource, /if \(!\/\[\?&\]range=\/\.test\(request\.uris\[0\]\)\)/)
  assert.match(shakaSource, /if \(!\/\[\?&\]alr=\/\.test\(request\.uris\[0\]\)\)/)
  assert.doesNotMatch(shakaSource, /searchParams\.set\('range'/)
  // FreeTube player.load(src, startTime, mimeType).
  assert.match(shakaSource, /player\.load\(src,\s*\/\* startTime \*\/ null,\s*'application\/dash\+xml'\)/)
})

test('desktop youtube prefers official toDash over remote and progressive', async () => {
  const source = await readFile(providerPath, 'utf8')

  const officialLocal = source.indexOf('Official youtubei.js DASH (VideoInfo.toDash)')
  const officialRemote = source.indexOf('Official YouTube-hosted DASH manifest URL')
  const progressive = source.indexOf('Progressive muxed')

  assert.notEqual(officialLocal, -1)
  assert.notEqual(officialRemote, -1)
  assert.notEqual(progressive, -1)
  assert.ok(officialLocal < officialRemote)
  assert.ok(officialRemote < progressive)
  assert.match(source, /scoreMappedPayload/)
})

test('desktop youtube provider exposes runtime prewarm', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /import \{ prewarmYoutubeiRuntime, resolveYoutubeiPayload \}/)
  assert.match(source, /export const prewarmYouTubePlayback = \(cookie = ''\) => \{[\s\S]*?return prewarmYoutubeiRuntime\(cookie\)/)
})

test('desktop youtube provider exposes tv oauth actions', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /export const resolveYouTubeOAuthSetup = \(\) => \{[\s\S]*?action: 'oauth-setup'/)
  assert.match(source, /export const resolveYouTubeOAuthStatus = \(\) => \{[\s\S]*?action: 'oauth-status'/)
  assert.match(source, /export const resolveYouTubeOAuthRevoke = \(\) => \{[\s\S]*?action: 'oauth-revoke'/)
})

test('desktop youtube login status uses tv oauth instead of cookie checks', async () => {
  const source = await readFile(siteLoginPath, 'utf8')

  assert.match(source, /if \(profile\.siteName === 'youtube'\) \{[\s\S]*?return buildYouTubeDesktopLoginStatus\(profile\)/)
  assert.match(source, /const buildYouTubeDesktopLoginStatus = async \(profile\) => \{[\s\S]*?resolveYouTubeOAuthStatus\(\)/)
})

test('desktop youtube uses MWEB toDash with mandatory content-bound PO Token', async () => {
  const source = await readFile(corePath, 'utf8')

  // A remote WEB session supplies visitor data; MWEB supplies classic adaptive
  // URLs, and its video-bound token authorizes distant googlevideo byte ranges.
  // FreeTube getLocalVideoInfo uses generateSessionLocally:false + WEB bootstrap;
  // local ANDROID sessions intermittently LOGIN_REQUIRED every official client.
  // OAuth is never the primary streaming session.
  assert.match(source, /const OFFICIAL_PLAYBACK_CLIENTS = \['MWEB'\]/)
  assert.match(source, /const OFFICIAL_FALLBACK_CLIENTS = \['ANDROID', 'WEB'\]/)
  assert.match(source, /const AUTH_GATE_PLAYBACK_CLIENTS = \['TV', 'WEB'\]/)
  // Electron main uses node youtubei.js + file UniversalCache (not /web IndexedDB).
  assert.match(source, /from 'youtubei\.js'/)
  assert.doesNotMatch(source, /from 'youtubei\.js\/web'/)
  assert.match(source, /createPlayerCache/)
  assert.match(source, /createPlaybackRuntime/)
  assert.match(source, /getPlaybackRuntime/)
  assert.match(source, /generate_session_locally:\s*false/)
  assert.match(source, /retrieve_innertube_config:\s*true/)
  assert.match(source, /client_type: 'WEB'/)
  assert.match(source, /invalidatePlaybackRuntime/)
  assert.match(source, /MAX_PLAYBACK_SESSION_REBUILDS/)
  assert.match(source, /function scoreFormatSet\(/)
  assert.match(source, /bestCandidate/)
  assert.match(source, /buildPlaybackFailureError/)
  assert.match(source, /auth_fallback: 'oauth-gate'/)
  assert.match(source, /resolveFormatsWithRuntime/)
  assert.match(source, /preferPoToken: false/)
  assert.match(source, /preferPoToken: true/)
  assert.match(source, /const requiresPoToken = preferPoToken && \(client === 'MWEB' \|\| client === 'WEB'\)/)
  assert.match(source, /Content-bound PO Token unavailable for \$\{client\}/)
  assert.match(source, /runtime\.yt\.session\.player\.po_token = undefined/)
  assert.match(source, /poToken: activePoToken \|\| undefined/)
  // IOS manifests can start but their far ranges reject this token; never make
  // that unverified path the default merely because toDash() returned XML.
  assert.doesNotMatch(source, /const OFFICIAL_PLAYBACK_CLIENTS = \[[^\]]*'IOS'/)
  // Official toDash scores highest and stops the client loop.
  assert.match(source, /if \(score >= 4\)/)
  assert.match(source, /localDashManifest/)
  // Must not route playback through OAuth session first.
  assert.doesNotMatch(source, /const AUTHENTICATED_PLAYBACK_CLIENTS/)
  assert.doesNotMatch(source, /const ANONYMOUS_CLIENTS = \['IOS'/)
  // Must not boot the playback session as ANDROID local (poisoned visitor).
  assert.doesNotMatch(source, /createPlaybackRuntime[\s\S]*?client_type: 'ANDROID'/)
})

test('desktop youtube playback resolve does not reference undeclared cache binding', async () => {
  const source = await readFile(providerPath, 'utf8')
  const fnStart = source.indexOf('export async function resolveYouTubePlayback')
  assert.notEqual(fnStart, -1)
  const fnBody = source.slice(fnStart, fnStart + 1800)

  // `cached` must be declared in function scope before any read (previously a
  // block-scoped const caused ReferenceError and broke all YouTube playback).
  assert.match(fnBody, /let cached = null/)
  assert.doesNotMatch(fnBody, /const maxAttempts = cached \? 1 : 2/)
})

test('desktop youtube oauth state path falls back to monorepo config file', async () => {
  const source = await readFile(corePath, 'utf8')
  const mainSource = await readFile(mainPath, 'utf8')

  assert.match(source, /import \{ youtubeOAuthStateFilePath \} from '\.\.\/\.\.\/\.\.\/constants\.mjs'/)
  assert.match(source, /function getOAuthStateFilePath\(\) \{[\s\S]*?youtubeOAuthStateFilePath/)
  assert.doesNotMatch(source, /return process\.env\.YOUTUBE_OAUTH_STATE_FILE \|\| null/)
  assert.match(mainSource, /process\.env\.YOUTUBE_OAUTH_STATE_FILE = youtubeOAuthStateFilePath/)
})

test('youtube tv oauth opens the youtube activation page', async () => {
  const desktopSource = await readFile(corePath, 'utf8')
  const pluginSource = await readFile(pluginCorePath, 'utf8')

  assert.match(desktopSource, /const YOUTUBE_TV_ACTIVATION_URL = 'https:\/\/www\.youtube\.com\/activate'/)
  assert.match(pluginSource, /const YOUTUBE_TV_ACTIVATION_URL = 'https:\/\/www\.youtube\.com\/activate'/)
  assert.doesNotMatch(desktopSource, /verification_url: data\.verification_url/)
  assert.doesNotMatch(pluginSource, /verification_url: data\.verification_url/)
})

test('youtube captions treat tv oauth as an authenticated session', async () => {
  const desktopSource = await readFile(corePath, 'utf8')
  const pluginSource = await readFile(pluginCorePath, 'utf8')

  assert.match(desktopSource, /const hasAuth = runtime\.authMode === 'oauth' \|\| runtime\.authMode === 'cookie';[\s\S]*?const clients = hasAuth \? CAPTIONS_AUTHENTICATED_CLIENTS : CAPTIONS_ANONYMOUS_CLIENTS;/)
  assert.match(pluginSource, /const hasAuth = runtime\.authMode === 'oauth' \|\| runtime\.authMode === 'cookie';[\s\S]*?const clients = hasAuth \? CAPTIONS_AUTHENTICATED_CLIENTS : CAPTIONS_ANONYMOUS_CLIENTS;/)
})

test('desktop youtube subtitles are resolved through the electron bridge', async () => {
  const providerSource = await readFile(providerPath, 'utf8')
  const ipcSource = await readFile(ipcPlaybackPath, 'utf8')
  const frontendSource = await readFile(frontendDetailPath, 'utf8')

  assert.match(providerSource, /export async function resolveYouTubeSubtitles/)
  assert.match(ipcSource, /desktop:resolve-youtube-subtitles/)
  assert.match(frontendSource, /desktopBridge\.resolveYouTubeSubtitles\(videoUrl/)
  assert.match(frontendSource, /content,/)
  assert.doesNotMatch(frontendSource, /\/api\/video\/subtitles/)
})

test('desktop youtube auth does not merge cookies into playback requests', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.doesNotMatch(source, /youtubeCookieFilePath/)
  assert.doesNotMatch(source, /readYoutubeCookieFileHeader/)
  assert.doesNotMatch(source, /isYouTubeCookieTarget/)
  assert.doesNotMatch(source, /prewarmYouTubePlayback\(cookie\)/)
  assert.doesNotMatch(source, /resolveYouTubePlayback\(normalizedUrl,\s*\{\s*cookie/s)
  assert.doesNotMatch(source, /resolveYouTubeSubtitles\(normalizedUrl,\s*\{\s*cookie/s)
})

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const providerPath = new URL('../src/playback/providers/youtube/index.mjs', import.meta.url)
const corePath = new URL('../src/playback/providers/youtube/youtubei_core.mjs', import.meta.url)
const mainPath = new URL('../src/main.mjs', import.meta.url)
const siteLoginPath = new URL('../src/site-login.mjs', import.meta.url)
const ipcHandlersPath = new URL('../src/ipc-handlers.mjs', import.meta.url)
const ipcPlaybackPath = new URL('../src/ipc-playback.mjs', import.meta.url)
const pluginCorePath = new URL('../../squirrel-backend/sites/squirrel_youtube/node/youtubei_core.mjs', import.meta.url)
const frontendDetailPath = new URL('../renderer/src/features/video/composables/useVideoDetail.ts', import.meta.url)

test('desktop youtube provider keeps complete SABR and DASH payloads for direct playback', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /resolveYoutubeiPayload\(\{[\s\S]*?resolution_mode:\s*'all'/)
  assert.doesNotMatch(source, /include_local_dash_manifest:\s*false/)
  assert.match(source, /const PLAYBACK_CACHE_VERSION = 'mweb-sabr-v4'/)
  assert.match(source, /const cacheKey = `\$\{PLAYBACK_CACHE_VERSION\}\|\$\{videoId\}/)
  assert.match(source, /fallback_mpd_content: officialLocalDash \|\| null/)
  assert.match(source, /stream_type: 'sabr'/)
})

test('desktop youtube playback uses official youtubei.js and googlevideo only', async () => {
  const source = await readFile(providerPath, 'utf8')
  const coreSource = await readFile(corePath, 'utf8')

  // No homemade MPD builders / media proxy.
  assert.doesNotMatch(source, /buildFallbackLocalDashManifest/)
  assert.doesNotMatch(source, /buildRepresentationXml/)
  assert.doesNotMatch(source, /buildSegmentBaseXml/)
  assert.doesNotMatch(source, /representationGroupKey/)
  assert.doesNotMatch(source, /rewriteYouTubeMpdThroughProxy/)
  assert.doesNotMatch(source, /youtube-media-proxy/)

  // Official path: SABR-flavoured toDash and regular toDash run in parallel so
  // wall time is max(), not sum. Regular DASH stays available as Shaka fallback.
  assert.match(source, /VideoInfo\.toDash\(\)/)
  assert.match(source, /streaming_data\.dash_manifest_url/)
  assert.match(coreSource, /manifestInfo\.toDash\(/)
  assert.match(coreSource, /from 'googlevideo\/utils'/)
  assert.match(coreSource, /is_sabr: true/)
  assert.match(coreSource, /buildSabrFormat/)
  assert.match(coreSource, /server_abr_streaming_url/)
  assert.match(coreSource, /selectPlaybackAdaptiveFormats/)
  assert.match(coreSource, /format\?\.is_auto_dubbed/)
  assert.match(coreSource, /format\?\.is_original/)
  assert.match(coreSource, /selectSabrStartupFormats/)
  // Per-height best itag (VP9 preferred at a height) — never a global codec lock.
  assert.match(coreSource, /sabrVideoCodecRank/)
  assert.doesNotMatch(
    coreSource,
    /const selectedVideoFamily = \['vp9', 'avc', 'av1'\]/,
  )
  assert.match(coreSource, /Promise\.all\(\[\s*buildSabrPlayback\(/)
  assert.match(coreSource, /buildLocalDashManifest\(videoInfo, \{\s*poToken:/)
})

test('renderer youtube SABR uses googlevideo + Shaka with DASH fallback', async () => {
  const opsPath = new URL(
    '../renderer/src/features/video/composables/useVideoOperations.ts',
    import.meta.url,
  )
  const shakaPath = new URL(
    '../renderer/src/features/playback/components/video-player/adapters/ShakaDashAdapter.ts',
    import.meta.url,
  )
  const sabrShakaPath = new URL(
    '../renderer/src/features/playback/components/video-player/adapters/SabrShakaPlayerAdapter.ts',
    import.meta.url,
  )
  const opsSource = await readFile(opsPath, 'utf8')
  const shakaSource = await readFile(shakaPath, 'utf8')
  const sabrShakaSource = await readFile(sabrShakaPath, 'utf8')
  const providerSource = await readFile(providerPath, 'utf8')

  // FreeTube Watch.createLocalDashManifest style data: URL for official toDash body.
  assert.match(opsSource, /data:application\/dash\+xml;charset=UTF-8/)
  assert.match(opsSource, /playbackEngine:\s*'shaka'/)
  assert.match(opsSource, /isYouTubeOfficialDash/)
  assert.match(opsSource, /isYouTubeSabr/)
  assert.match(opsSource, /fallbackSrc:/)

  // MIT GoogleVideo integration, scoped to sabr: so other providers retain
  // Shaka's built-in HTTP/HTTPS transports.
  assert.match(shakaSource, /new SabrStreamingAdapter/)
  assert.match(shakaSource, /new SabrShakaPlayerAdapter/)
  assert.match(shakaSource, /SABR load failed; falling back to DASH/)
  assert.match(sabrShakaSource, /registerScheme\(\s*'sabr'/)
  assert.doesNotMatch(sabrShakaSource, /registerScheme\(\s*'https?'/)
  assert.match(sabrShakaSource, /new SabrUmpProcessor/)
  assert.match(sabrShakaSource, /activeNetworkRequests >= 2/)
  assert.match(sabrShakaSource, /acquireNetworkSlot/)

  // FreeTube googlevideo videoplayback filters (POST + alr + http-body redirect).
  assert.match(shakaSource, /installYouTubeNetworkingFilters/)
  assert.match(shakaSource, /alr=yes/)
  assert.match(shakaSource, /request\.method = 'POST'/)
  assert.match(shakaSource, /HTTP_IN_HEX/)
  // Startup-tuned buffer goals: SABR keeps a short forward window so first
  // media isn't a multi-segment storm; rebufferingGoal still FreeTube 0.02.
  assert.match(shakaSource, /bufferingGoal:\s*source\.sabr \? 12 : 60/)
  assert.match(shakaSource, /bufferBehind:\s*source\.sabr \? 30 : 120/)
  assert.match(shakaSource, /rebufferingGoal:\s*0\.02/)
  assert.match(shakaSource, /restrictToElementSize:\s*false/)
  // FreeTube pins ~720p after first load (ABR off during load, then re-enabled).
  assert.match(shakaSource, /applyStartupQuality/)
  assert.match(shakaSource, /restoreAbrAfterStartupPin/)
  assert.match(shakaSource, /STARTUP_QUALITY_HEIGHT = 1080/)
  assert.match(shakaSource, /pickStartupVariantTrack/)
  assert.match(shakaSource, /enabled: false/)
  // SABR menu rows must come from the playable SABR format ladder.
  assert.match(providerSource, /sabrMenuFormats/)
  assert.match(providerSource, /normalizeMenuFormat/)

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
  assert.match(engineSource, /const seek = async \(time: number\) => \{[\s\S]*?streamOwned/)
  assert.match(engineSource, /coordinator\.beginSeek/)
  assert.match(engineSource, /coordinator\.getSnapshot\(\)\.intent === 'play'/)
  assert.doesNotMatch(engineSource, /resumeAfterSeek/)
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
  // Audio time can keep advancing while Chromium's video decoder is frozen.
  // Verify seek health with presented frames, then rebuild/reload in place.
  assert.match(shakaSource, /requestVideoFrameCallback/)
  assert.match(shakaSource, /shouldRecoverVideoAfterSeek/)
  assert.match(shakaSource, /selectVariantTrack\(activeTrack, true, 0\)/)
  assert.match(shakaSource, /reloadManifestAfterFrozenSeek/)
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

test('desktop youtube prefers SABR, then official DASH, then remote and progressive', async () => {
  const source = await readFile(providerPath, 'utf8')

  const sabr = source.indexOf("stream_type: 'sabr'")
  const officialLocal = source.indexOf('Official youtubei.js DASH (VideoInfo.toDash)')
  const officialRemote = source.indexOf('Official YouTube-hosted DASH manifest URL')
  const progressive = source.indexOf('Progressive muxed')

  assert.notEqual(sabr, -1)
  assert.notEqual(officialLocal, -1)
  assert.notEqual(officialRemote, -1)
  assert.notEqual(progressive, -1)
  assert.ok(sabr < officialLocal)
  assert.ok(officialLocal < officialRemote)
  assert.ok(officialRemote < progressive)
  assert.match(source, /scoreMappedPayload/)
})

test('desktop youtube provider exposes runtime prewarm', async () => {
  const source = await readFile(providerPath, 'utf8')
  const coreSource = await readFile(corePath, 'utf8')

  assert.match(source, /import \{ prewarmYoutubeiRuntime, resolveYoutubeiPayload \}/)
  assert.match(source, /export const prewarmYouTubePlayback = \(cookie = ''\) => \{[\s\S]*?return prewarmYoutubeiRuntime\(cookie\)/)
  assert.match(coreSource, /const PLAYBACK_RUNTIME_IN_FLIGHT = new Map\(\)/)
  assert.match(coreSource, /const PO_TOKEN_MINTER_WARMUPS = new WeakMap\(\)/)
  assert.match(coreSource, /function warmPoTokenMinter\(runtime\)/)
  assert.match(coreSource, /export async function prewarmYoutubeiRuntime[\s\S]*?await warmPoTokenMinter\(runtime\)/)
  assert.match(coreSource, /async function buildPoToken[\s\S]*?await warmPoTokenMinter\(runtime\)/)
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
  assert.match(source, /const hasOAuthCredentials = Boolean\(readStoredOAuthTokens\(\)\)/)
  assert.match(source, /&& hasOAuthCredentials[\s\S]*?const oauthRuntime = await getOAuthRuntime\(\)/)
  // Must not boot the playback session as ANDROID local (poisoned visitor).
  assert.doesNotMatch(source, /createPlaybackRuntime[\s\S]*?client_type: 'ANDROID'/)
})

test('desktop youtube playback uses scoped cache as stale-while-revalidate', async () => {
  const source = await readFile(providerPath, 'utf8')
  const fnStart = source.indexOf('export async function resolveYouTubePlayback')
  assert.notEqual(fnStart, -1)
  const fnBody = source.slice(fnStart, fnStart + 1800)

  // Cache hit returns official DASH immediately while one deduplicated refresh
  // updates the short-lived signed URLs for the next navigation.
  assert.match(fnBody, /const cached = forceRefresh \? null : await cache\.getCachedPayload\(cacheKey\)/)
  assert.match(fnBody, /scoreMappedPayload\(cached\) >= 2000/)
  assert.match(fnBody, /void refreshYouTubePlayback\(params\)/)
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

test('youtube oauth tokens are unwrapped before signIn and persistence', async () => {
  const desktopSource = await readFile(corePath, 'utf8')
  const pluginSource = await readFile(pluginCorePath, 'utf8')

  for (const source of [desktopSource, pluginSource]) {
    assert.match(source, /function normalizeOAuthTokens\(/)
    assert.match(source, /function readStoredOAuthTokens\(/)
    assert.match(source, /function persistOAuthCredentials\(/)
    assert.match(source, /oauthTokensFromSession/)
    // Must never re-nest the event object `{ credentials }` into state.credentials.
    assert.doesNotMatch(
      source,
      /yt\.session\.on\('auth', \(\{ credentials \}\) => \{\s*saveOAuthState\(\{ pending: false, credentials \}\)/,
    )
    assert.doesNotMatch(
      source,
      /yt\.session\.on\('update-credentials', \(credentials\) => \{\s*persistOAuthCredentials\(credentials \|\| yt\.session\.credentials\)/,
    )
  }

  assert.match(desktopSource, /YOUTUBE_VIDEO_UNAVAILABLE/)
  assert.match(desktopSource, /attemptLooksLikePermanentUnavailability/)
  assert.match(desktopSource, /playability_subreason/)
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

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const providerPath = new URL('../src/playback/providers/youtube/index.mjs', import.meta.url)
const corePath = new URL('../src/playback/providers/youtube/youtubei_core.mjs', import.meta.url)
const mainPath = new URL('../src/main.mjs', import.meta.url)
const pluginCorePath = new URL('../../squirrel-plugins/youtube/src/squirrel_youtube/node/youtubei_core.mjs', import.meta.url)
const frontendDetailPath = new URL('../../squirrel-frontend/src/composables/useVideoDetail.ts', import.meta.url)

test('desktop youtube provider keeps complete dash payload for direct playback', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /resolveYoutubeiPayload\(\{[\s\S]*?resolution_mode:\s*'all'/)
  assert.doesNotMatch(source, /include_local_dash_manifest:\s*false/)
})

test('desktop youtube provider prefers local dash manifests before remote manifests', async () => {
  const source = await readFile(providerPath, 'utf8')
  const localManifestIndex = source.indexOf('const localDashManifest = response?.local_dash_manifest || buildFallbackLocalDashManifest(formats)')
  const dashManifestIndex = source.indexOf('if (hasAdaptiveSet && dashManifestUrl)')

  assert.notEqual(localManifestIndex, -1)
  assert.notEqual(dashManifestIndex, -1)
  assert.ok(localManifestIndex < dashManifestIndex)
})

test('desktop youtube provider serializes segment ranges for local dash manifests', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /const serializeRange = \(range\) => \{[\s\S]*?return `\$\{start\}-\$\{end\}`/)
  assert.doesNotMatch(source, /indexRange="\$\{escapeXml\(format\.index_range\)\}"/)
  assert.doesNotMatch(source, /Initialization range="\$\{escapeXml\(format\.init_range\)\}"/)
})

test('desktop youtube provider includes duration in generated dash manifests', async () => {
  const source = await readFile(providerPath, 'utf8')

  assert.match(source, /mediaPresentationDuration="\$\{escapeXml\(mediaPresentationDuration\)\}"/)
  assert.match(source, /new URL\(format\?\.url \|\| ''\)\.searchParams\.get\('dur'\)/)
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
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /if \(profile\.siteName === 'youtube'\) \{[\s\S]*?return buildYouTubeDesktopLoginStatus\(profile\)/)
  assert.match(source, /const buildYouTubeDesktopLoginStatus = async \(profile\) => \{[\s\S]*?resolveYouTubeOAuthStatus\(\)/)
})

test('desktop youtube client order defers expensive mweb po token generation', async () => {
  const source = await readFile(corePath, 'utf8')

  assert.match(source, /const AUTHENTICATED_PLAYBACK_CLIENTS = \['ANDROID', 'WEB', 'TV', 'MWEB'\]/)
  assert.match(source, /const AUTHENTICATED_FULL_CLIENTS = \['ANDROID', 'WEB', 'TV', 'MWEB'\]/)
})

test('desktop youtube oauth state path is read at runtime', async () => {
  const source = await readFile(corePath, 'utf8')

  assert.match(source, /return process\.env\.YOUTUBE_OAUTH_STATE_FILE \|\| null/)
  assert.doesNotMatch(source, /const OAUTH_STATE_FILE = process\.env\.YOUTUBE_OAUTH_STATE_FILE/)
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
  const mainSource = await readFile(mainPath, 'utf8')
  const frontendSource = await readFile(frontendDetailPath, 'utf8')

  assert.match(providerSource, /export async function resolveYouTubeSubtitles/)
  assert.match(mainSource, /desktop:resolve-youtube-subtitles/)
  assert.match(frontendSource, /bridge\.resolveYouTubeSubtitles\(videoUrl/)
  assert.match(frontendSource, /content,/)
  assert.match(frontendSource, /url: `\/api\/video\/subtitles\?\$\{params\.toString\(\)\}`/)
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

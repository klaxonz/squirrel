import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const providerPath = new URL('../src/playback/providers/youtube/index.mjs', import.meta.url)
const corePath = new URL('../src/playback/providers/youtube/youtubei_core.mjs', import.meta.url)

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

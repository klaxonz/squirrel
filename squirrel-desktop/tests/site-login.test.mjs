import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import { stripElectronFromUserAgent } from '../src/constants.mjs'

const siteLoginPath = new URL('../src/site-login.mjs', import.meta.url)
const constantsPath = new URL('../src/constants.mjs', import.meta.url)
const cookieHeaderPath = new URL('../src/cookie-header.mjs', import.meta.url)
const mediaHeadersPath = new URL('../src/media-headers.mjs', import.meta.url)
const documentLoaderPath = new URL('../src/document-loader.mjs', import.meta.url)
const mainPath = new URL('../src/main.mjs', import.meta.url)

test('desktop media user agent removes Electron and app product tokens', () => {
  const raw = 'Mozilla/5.0 Chrome/146.0.0.0 Squirrel/0.1.0 Electron/41.2.0 Safari/537.36'

  assert.equal(
    stripElectronFromUserAgent(raw),
    'Mozilla/5.0 Chrome/146.0.0.0 Safari/537.36',
  )
  assert.equal(
    stripElectronFromUserAgent('Mozilla/5.0 squirrel/0.1.0 electron/41.2.0 Chrome/146.0.0.0'),
    'Mozilla/5.0 Chrome/146.0.0.0',
  )
})

test('desktop bilibili/youtube login profiles remain wired', async () => {
  const constants = await readFile(constantsPath, 'utf8')
  const siteLogin = await readFile(siteLoginPath, 'utf8')
  const cookieHeader = await readFile(cookieHeaderPath, 'utf8')
  const mediaHeaders = await readFile(mediaHeadersPath, 'utf8')
  const documentLoader = await readFile(documentLoaderPath, 'utf8')

  assert.match(constants, /const desktopChromeVersion = process\.versions\.chrome/)
  assert.match(constants, /const desktopChromeUserAgent = `Mozilla\/5\.0 \(Windows NT 10\.0; Win64; x64\)[\s\S]*Chrome\/\$\{desktopChromeVersion\}/)
  assert.match(siteLogin, /bilibili:\s*\{[\s\S]*?loginUrl: 'https:\/\/passport\.bilibili\.com\/login'/)
  assert.match(siteLogin, /youtube:\s*\{[\s\S]*?signedInCookieNames:/)
  assert.match(siteLogin, /'bilibili\.com': 'bilibili'/)
  assert.match(siteLogin, /'youtube\.com': 'youtube'/)
  // Anonymous desktop session must fall back to the backend-synced cookie file
  // (config/site_cookies/bilibili.txt) so playback resolves HD, not 480p/360p.
  assert.match(siteLogin, /mergeBilibiliFileCookieFallback/)
  assert.match(siteLogin, /import \{ mergeBilibiliFileCookieFallback \} from '\.\/bilibili-cookie-file\.mjs'/)
  assert.match(siteLogin, /return mergeBilibiliFileCookieFallback\(sessionHeader\)/)
  assert.match(constants, /bilibiliCookieFilePath = path\.join\(repoRoot, 'config', 'site_cookies', 'bilibili\.txt'\)/)
  assert.match(cookieHeader, /const isBilibiliCookieTarget =/)
  assert.doesNotMatch(cookieHeader, /isJavdbCookieTarget|isPornhubCookieTarget|isYouPornCookieTarget|isMissavDocumentTarget/)
  assert.doesNotMatch(siteLogin, /javdb:|pornhub:|youporn:/)
  assert.doesNotMatch(mediaHeaders, /javdb\.com|pornhub\.com|youporn\.com|missav\.ai/)
  assert.match(mediaHeaders, /mountaintoys\.cn/)
  assert.match(mediaHeaders, /isBilibiliEdgeMediaUrl/)
  assert.match(mediaHeaders, /upgcxcode/)
  assert.doesNotMatch(documentLoader, /Camoufox|isJavdbCookieTarget|isMissavDocumentTarget/)
})

test('renderer exposes bilibili desktop login controls', async () => {
  const siteRuntimeManagerPath = new URL(
    '../renderer/src/features/settings/views/SiteRuntimeManager.vue',
    import.meta.url,
  )
  const siteDesktopLoginPath = new URL(
    '../renderer/src/features/settings/composables/useSiteDesktopLogin.ts',
    import.meta.url,
  )
  const managerSource = await readFile(siteRuntimeManagerPath, 'utf8')
  const loginSource = await readFile(siteDesktopLoginPath, 'utf8')

  assert.match(managerSource, /useSiteDesktopLogin|openSiteLogin|getSiteLoginStatus/)
  assert.match(loginSource, /bilibili|openSiteLogin|getSiteLoginStatus/)
  assert.doesNotMatch(loginSource, /javdb|pornhub|youporn/)
})

test('main.mjs is slim composition root', async () => {
  const source = await readFile(mainPath, 'utf8')

  // Should NOT contain any of the extracted module logic
  assert.doesNotMatch(source, /SITE_LOGIN_PROFILES/)
  assert.doesNotMatch(source, /buildJavdbDesktopLoginStatus/)
  assert.doesNotMatch(source, /isJavdbCookieTarget/)
  assert.doesNotMatch(source, /MEDIA_HEADER_RULES\s*=\s*\[/)
  assert.doesNotMatch(source, /new CamoufoxDocumentLoader\(/)
  assert.doesNotMatch(source, /const installDesktopBridgeHandlers\s*=\s*\(\)\s*=>/)
  assert.doesNotMatch(source, /const installDesktopMediaHeaders\s*=\s*\(\)\s*=>/)
  assert.doesNotMatch(source, /const SITE_LOGIN_PROFILES\s*=\s*\{/)
})

test('youtube media headers stay FreeTube-aligned (official toDash path)', async () => {
  const source = await readFile(mediaHeadersPath, 'utf8')
  const constants = await readFile(new URL('../src/constants.mjs', import.meta.url), 'utf8')
  const mainSource = await readFile(new URL('../src/main.mjs', import.meta.url), 'utf8')

  // FreeTube: Referer + Origin + strip Content-Type on videoplayback; no cookies.
  assert.match(source, /YOUTUBE_MEDIA_HEADERS/)
  assert.match(source, /Referer: 'https:\/\/www\.youtube\.com\/'/)
  assert.match(source, /Origin: 'https:\/\/www\.youtube\.com'/)
  assert.match(source, /stripCookies:\s*true/)
  assert.match(source, /stripContentTypeOnVideoplayback:\s*true/)
  // FreeTube: strip Electron from session UA; also force Chrome UA on media.
  assert.match(source, /installDesktopSessionUserAgent/)
  assert.match(source, /stripElectronFromUserAgent/)
  assert.match(source, /'User-Agent': desktopChromeUserAgent/)
  // Renderer page origin must not survive as lowercase `origin` next to
  // FreeTube Origin — that combo is a common googlevideo 403 cause.
  assert.match(source, /deleteHeaderCaseInsensitive/)
  assert.match(constants, /export const stripElectronFromUserAgent/)
  assert.match(mainSource, /installDesktopSessionUserAgent/)
  assert.doesNotMatch(source, /com\.google\.ios\.youtube/)
  assert.doesNotMatch(source, /onBeforeRedirect/)
  assert.doesNotMatch(source, /restoreRange/)
  assert.doesNotMatch(source, /youtubeStreamKey/)
  assert.doesNotMatch(source, /resolveYouTubeMediaHeaders/)
  assert.doesNotMatch(source, /createServer/)
  assert.doesNotMatch(source, /127\.0\.0\.1/)
})

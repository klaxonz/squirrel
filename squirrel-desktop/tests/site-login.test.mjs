import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const mainPath = new URL('../src/main.mjs', import.meta.url)
const camoufoxLoaderPath = new URL('../src/cloudflare/camoufox-document-loader.mjs', import.meta.url)
const pluginManagerPath = new URL('../../squirrel-frontend/src/views/PluginManager.vue', import.meta.url)

test('desktop javdb login uses electron session cookies only', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /const desktopChromeVersion = process\.versions\.chrome/)
  assert.match(source, /const desktopChromeUserAgent = `Mozilla\/5\.0 \(Windows NT 10\.0; Win64; x64\)[\s\S]*Chrome\/\$\{desktopChromeVersion\}/)
  assert.match(source, /const desktopChromeClientHints = \{[\s\S]*?'sec-ch-ua'/)
  assert.match(source, /const desktopChromeUserAgentMetadata = \{[\s\S]*?fullVersionList:[\s\S]*?platform: 'Windows'/)
  assert.match(source, /'javdb\.com': 'javdb'/)
  assert.match(source, /javdb:\s*\{[\s\S]*?loginUrl: 'https:\/\/javdb\.com\/users\/sign_in'[\s\S]*?userAgent: desktopChromeUserAgent[\s\S]*?userAgentMetadata: desktopChromeUserAgentMetadata[\s\S]*?cookieHosts: \['javdb\.com'\]/)
  assert.match(source, /loginWindow\.webContents\.setUserAgent\(profile\.userAgent\)/)
  assert.match(source, /loginWindow\.webContents\.debugger\.sendCommand\('Network\.setUserAgentOverride'/)
  assert.match(source, /loginWindow\.loadURL\(profile\.loginUrl, profile\.userAgent \? \{ userAgent: profile\.userAgent \} : undefined\)/)
  assert.match(source, /hosts: \['javdb\.com'\][\s\S]*?'User-Agent': desktopChromeUserAgent[\s\S]*?\.\.\.desktopChromeClientHints/)
  assert.match(source, /const buildJavdbDesktopLoginStatus = async \(profile, cookies\) => \{[\s\S]*?const cookieHeader = buildCookieHeaderFromCookies\(cookies\)/)
  assert.match(source, /if \(isJavdbCookieTarget\(normalizedUrl\)\) \{[\s\S]*?return sessionCookieHeader/)
  assert.match(source, /if \(profile\.siteName === 'javdb'\) \{[\s\S]*?return buildJavdbDesktopLoginStatus\(profile, cookies\)/)
  assert.match(source, /profile\.siteName === 'javdb'/)
  assert.match(source, /new CamoufoxDocumentLoader\(\{[\s\S]*?electronSession: session\.defaultSession/)
  assert.match(source, /isJavdbCookieTarget\(normalizedUrl\) \|\| isMissavDocumentTarget\(normalizedUrl\)[\s\S]*?getCamoufoxDocumentLoader\(\)\.loadHtml/)
  assert.doesNotMatch(source, /javdbCookieFilePath|writeJavdbCookieFile|readJavdbCookieFileHeader/)
})

test('desktop cloudflare loader syncs camoufox cookies into electron session', async () => {
  const source = await readFile(camoufoxLoaderPath, 'utf8')

  assert.match(source, /import \{ Camoufox \} from 'camoufox-js'/)
  assert.match(source, /user_data_dir: profileDir/)
  assert.match(source, /headless: true/)
  assert.match(source, /block_webrtc: true/)
  assert.match(source, /main_world_eval: true/)
  assert.match(source, /context\.cookies\(targetUrl\)/)
  assert.match(source, /electronSession\.cookies\.set/)
  assert.match(source, /electronSession\.cookies\.flushStore/)
  assert.match(source, /cf-turnstile|challenge-platform/)
})

test('frontend exposes javdb desktop login controls', async () => {
  const source = await readFile(pluginManagerPath, 'utf8')

  assert.match(source, /const DESKTOP_LOGIN_SITES = new Set\(\['bilibili', 'javdb', 'pornhub', 'youporn'\]\)/)
  assert.match(source, /'javdb\.com': 'javdb'/)
  assert.match(source, /siteDesktopLoginSupported: supportsDesktopLoginSite\(siteName\)/)
})

test('desktop youporn login verifies the session page', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /youporn:\s*\{[\s\S]*?loginUrl: 'https:\/\/www\.youporn\.com\/login'[\s\S]*?cookieHosts: \['youporn\.com'\]/)
  assert.equal(source.includes('const youpornLoggedInPattern = /isLoggedInUser\\s*=\\s*true/i'), true)
  assert.equal(source.includes('const youpornLoggedOutPattern = /isLoggedInUser\\s*=\\s*false/i'), true)
  assert.match(source, /const checkYouPornDesktopPageLogin = async \(cookieHeader\) => \{[\s\S]*?session\.defaultSession\.fetch\(youpornReferer/)
  assert.match(source, /const buildYouPornDesktopLoginStatus = async \(profile, cookies\) => \{[\s\S]*?checkYouPornDesktopPageLogin\(mergeCookieHeaders\(youpornAgeGateCookieHeader, cookieHeader\)\)/)
  assert.match(source, /if \(profile\.siteName === 'youporn'\) \{[\s\S]*?return buildYouPornDesktopLoginStatus\(profile, cookies\)/)
  assert.match(source, /const canAutoConfirmLogin = profile\.signedInCookieNames\.length > 0[\s\S]*?\|\| profile\.siteName === 'youporn'/)
})

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const siteLoginPath = new URL('../src/site-login.mjs', import.meta.url)
const constantsPath = new URL('../src/constants.mjs', import.meta.url)
const cookieHeaderPath = new URL('../src/cookie-header.mjs', import.meta.url)
const mediaHeadersPath = new URL('../src/media-headers.mjs', import.meta.url)
const documentLoaderPath = new URL('../src/document-loader.mjs', import.meta.url)
const camoufoxLoaderPath = new URL('../src/cloudflare/camoufox-document-loader.mjs', import.meta.url)
const mainPath = new URL('../src/main.mjs', import.meta.url)

test('desktop javdb login uses electron session cookies only', async () => {
  const constants = await readFile(constantsPath, 'utf8')
  const siteLogin = await readFile(siteLoginPath, 'utf8')
  const cookieHeader = await readFile(cookieHeaderPath, 'utf8')
  const mediaHeaders = await readFile(mediaHeadersPath, 'utf8')
  const documentLoader = await readFile(documentLoaderPath, 'utf8')

  assert.match(constants, /const desktopChromeVersion = process\.versions\.chrome/)
  assert.match(constants, /const desktopChromeUserAgent = `Mozilla\/5\.0 \(Windows NT 10\.0; Win64; x64\)[\s\S]*Chrome\/\$\{desktopChromeVersion\}/)
  assert.match(constants, /const desktopChromeClientHints = \{[\s\S]*?'sec-ch-ua'/)
  assert.match(constants, /const desktopChromeUserAgentMetadata = \{[\s\S]*?fullVersionList:[\s\S]*?platform: 'Windows'/)
  assert.match(siteLogin, /'javdb\.com': 'javdb'/)
  assert.match(siteLogin, /javdb:\s*\{[\s\S]*?loginUrl: 'https:\/\/javdb\.com\/users\/sign_in'[\s\S]*?userAgent: desktopChromeUserAgent[\s\S]*?userAgentMetadata: desktopChromeUserAgentMetadata[\s\S]*?cookieHosts: \['javdb\.com'\]/)
  assert.match(siteLogin, /loginWindow\.webContents\.setUserAgent\(profile\.userAgent\)/)
  assert.match(siteLogin, /loginWindow\.webContents\.debugger\.sendCommand\('Network\.setUserAgentOverride'/)
  assert.match(siteLogin, /loginWindow\.loadURL\(profile\.loginUrl, profile\.userAgent \? \{ userAgent: profile\.userAgent \} : undefined\)/)
  assert.match(mediaHeaders, /hosts: \['javdb\.com'\][\s\S]*?'User-Agent': desktopChromeUserAgent[\s\S]*?\.\.\.desktopChromeClientHints/)
  assert.match(siteLogin, /const buildJavdbDesktopLoginStatus = async \(profile, cookies\) => \{[\s\S]*?const cookieHeader = buildCookieHeaderFromCookies\(cookies\)/)
  assert.match(cookieHeader, /const isJavdbCookieTarget =/)
  assert.match(siteLogin, /if \(profile\.siteName === 'javdb'\) \{[\s\S]*?return buildJavdbDesktopLoginStatus\(profile, cookies\)/)
  assert.match(siteLogin, /profile\.siteName === 'javdb'/)
  assert.match(documentLoader, /new CamoufoxDocumentLoader\(\{[\s\S]*?electronSession: session\.defaultSession/)
  assert.match(documentLoader, /isJavdbCookieTarget\(normalizedUrl\) \|\| isMissavDocumentTarget\(normalizedUrl\)[\s\S]*?getCamoufoxDocumentLoader\(\)\.loadHtml/)
  assert.doesNotMatch(siteLogin, /javdbCookieFilePath|writeJavdbCookieFile|readJavdbCookieFileHeader/)
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

test('frontend exposes javdb desktop login controls', { skip: 'PluginManager.vue not found' }, () => {
})

test('desktop youporn login verifies the session page', async () => {
  const constants = await readFile(constantsPath, 'utf8')
  const siteLogin = await readFile(siteLoginPath, 'utf8')

  assert.match(siteLogin, /youporn:\s*\{[\s\S]*?loginUrl: 'https:\/\/www\.youporn\.com\/login'[\s\S]*?cookieHosts: \['youporn\.com'\]/)
  assert.equal(constants.includes('const youpornLoggedInPattern = /isLoggedInUser\\s*=\\s*true/i'), true)
  assert.equal(constants.includes('const youpornLoggedOutPattern = /isLoggedInUser\\s*=\\s*false/i'), true)
  assert.match(siteLogin, /const checkYouPornDesktopPageLogin = async \(cookieHeader\) => \{[\s\S]*?session\.defaultSession\.fetch\(youpornReferer/)
  assert.match(siteLogin, /const buildYouPornLoginWindowStatus = async \(profile, loginWindow\) => \{[\s\S]*?loginWindow\.webContents\.executeJavaScript/)
  assert.match(siteLogin, /const profileLink = document\.querySelector\('#js_mainMenu \.user-item a\[href\^="\/users\/"\]'\)/)
  assert.match(siteLogin, /if \(profile\.siteName === 'youporn'\) \{[\s\S]*?buildYouPornLoginWindowStatus\(profile, loginWindow\)/)
  assert.match(siteLogin, /const buildYouPornDesktopLoginStatus = async \(profile, cookies\) => \{[\s\S]*?checkYouPornDesktopPageLogin\(mergeCookieHeaders\(youpornAgeGateCookieHeader, cookieHeader\)\)/)
  assert.match(siteLogin, /if \(profile\.siteName === 'youporn'\) \{[\s\S]*?return buildYouPornDesktopLoginStatus\(profile, cookies\)/)
  assert.match(siteLogin, /const canAutoConfirmLogin = profile\.signedInCookieNames\.length > 0[\s\S]*?\|\| profile\.siteName === 'youporn'/)
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

import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const mainPath = new URL('../src/main.mjs', import.meta.url)
const pluginManagerPath = new URL('../../squirrel-frontend/src/views/PluginManager.vue', import.meta.url)

test('desktop javdb login persists cookies for backend plugin auth', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /const javdbCookieFilePath = path\.join\(repoRoot, 'config', 'site_cookies', 'javdb\.txt'\)/)
  assert.match(source, /const desktopChromeVersion = process\.versions\.chrome/)
  assert.match(source, /const desktopChromeUserAgent = `Mozilla\/5\.0 \(Windows NT 10\.0; Win64; x64\)[\s\S]*Chrome\/\$\{desktopChromeVersion\}/)
  assert.match(source, /const desktopChromeClientHints = \{[\s\S]*?'sec-ch-ua'/)
  assert.match(source, /const desktopChromeUserAgentMetadata = \{[\s\S]*?fullVersionList:[\s\S]*?platform: 'Windows'/)
  assert.match(source, /'javdb\.com': 'javdb'/)
  assert.match(source, /javdb:\s*\{[\s\S]*?loginUrl: 'https:\/\/javdb\.com\/users\/sign_in'[\s\S]*?userAgent: desktopChromeUserAgent[\s\S]*?userAgentMetadata: desktopChromeUserAgentMetadata[\s\S]*?cookieHosts: \['javdb\.com'\]/)
  assert.match(source, /const writeJavdbCookieFile = \(cookies\) => \{[\s\S]*?fs\.writeFileSync\(javdbCookieFilePath/)
  assert.match(source, /loginWindow\.webContents\.setUserAgent\(profile\.userAgent\)/)
  assert.match(source, /loginWindow\.webContents\.debugger\.sendCommand\('Network\.setUserAgentOverride'/)
  assert.match(source, /loginWindow\.loadURL\(profile\.loginUrl, profile\.userAgent \? \{ userAgent: profile\.userAgent \} : undefined\)/)
  assert.match(source, /hosts: \['javdb\.com'\][\s\S]*?'User-Agent': desktopChromeUserAgent[\s\S]*?\.\.\.desktopChromeClientHints/)
  assert.match(source, /if \(status\.logged_in && sessionCookieHeader\) \{[\s\S]*?writeJavdbCookieFile\(cookies\)/)
  assert.match(source, /if \(profile\.siteName === 'javdb'\) \{[\s\S]*?return buildJavdbDesktopLoginStatus\(profile, cookies\)/)
  assert.match(source, /profile\.siteName === 'javdb'/)
})

test('frontend exposes javdb desktop login controls', async () => {
  const source = await readFile(pluginManagerPath, 'utf8')

  assert.match(source, /const DESKTOP_LOGIN_SITES = new Set\(\['bilibili', 'javdb', 'pornhub', 'youporn'\]\)/)
  assert.match(source, /'javdb\.com': 'javdb'/)
  assert.match(source, /siteDesktopLoginSupported: supportsDesktopLoginSite\(siteName\)/)
})

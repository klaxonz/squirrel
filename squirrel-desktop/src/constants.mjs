import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const __filename = fileURLToPath(import.meta.url)
export const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')

export const APP_NAME = 'Squirrel'
export const DEFAULT_APP_URL = 'http://127.0.0.1:8001'
export const SERVER_CONFIG_FILE = 'server-config.json'

export const desktopChromeVersion = process.versions.chrome || '124.0.0.0'
export const desktopChromeMajorVersion = desktopChromeVersion.split('.')[0] || '124'
export const desktopChromeUserAgent = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${desktopChromeVersion} Safari/537.36`
export const desktopChromeAcceptLanguage = 'en-US,en;q=0.9'
export const desktopChromeClientHints = {
  'sec-ch-ua': `"Chromium";v="${desktopChromeMajorVersion}", "Google Chrome";v="${desktopChromeMajorVersion}", "Not-A.Brand";v="99"`,
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
}
export const desktopChromeUserAgentMetadata = {
  brands: [
    { brand: 'Chromium', version: desktopChromeMajorVersion },
    { brand: 'Google Chrome', version: desktopChromeMajorVersion },
    { brand: 'Not-A.Brand', version: '99' },
  ],
  fullVersionList: [
    { brand: 'Chromium', version: desktopChromeVersion },
    { brand: 'Google Chrome', version: desktopChromeVersion },
    { brand: 'Not-A.Brand', version: '99.0.0.0' },
  ],
  fullVersion: desktopChromeVersion,
  platform: 'Windows',
  platformVersion: '10.0.0',
  architecture: 'x86',
  model: '',
  mobile: false,
}

export const pornhubCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'pornhub.txt')
export const youpornCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'youporn.txt')
export const youtubeOAuthStateFilePath = path.join(repoRoot, 'config', 'youtube_oauth.json')

export const pornhubAgeGateCookieHeader = 'age_verified=1; accessAgeDisclaimerPH=1; accessAgeDisclaimerUK=1; accessPH=1'
export const youpornAgeGateCookieHeader = 'showAgeDisclaimer=1; access=1; accessPH=1'

export const SITE_SESSION_STORAGE_TYPES = [
  'cookies',
  'filesystem',
  'indexdb',
  'localstorage',
  'serviceworkers',
  'cachestorage',
  'websql',
]

export const DOCUMENT_READ_TIMEOUT_MS = 10000

export const javdbOrigin = 'https://javdb.com'
export const javdbReferer = `${javdbOrigin}/`
export const javdbLoginCheckUrl = `${javdbOrigin}/users/collection_actors`
export const javdbLoginRedirectPattern = /\/users\/(?:sign_in|login)|\/(?:sign_in|login)/i
export const javdbLoginPagePattern = /<title>\s*sign in\s*\|\s*javdb|action="\/users\/sign_in"|name="user\[(?:login|email)\]"/i
export const javdbErrorPagePattern = /<title>\s*just a moment|cf-error-details|error code 502|bad gateway/i

export const pornhubOrigin = 'https://www.pornhub.com'
export const pornhubReferer = `${pornhubOrigin}/`
export const youpornOrigin = 'https://www.youporn.com'
export const youpornReferer = `${youpornOrigin}/`

export const pornhubLoggedInPattern = /"loggedIn(?:Context)?":\s*true/i
export const pornhubLoggedOutPattern = /"loggedIn(?:Context)?":\s*false/i
export const pornhubUsernamePattern = /"username"\s*:\s*"([^"]+)"/i
export const pornhubDataUsernamePattern = /data-username="([^"]+)"/i
export const pornhubProfileLinkPattern = /<a[^>]+class="username"[^>]+href="\/users\/([^"/?#]+)"/i
export const pornhubProfileBlockPattern = /<div[^>]+class="profile"[\s\S]*?class="js_userName"[^>]*>([^<]+)</i
export const pornhubProfileStatusPattern = /class="userUserStatus[^"]*">\s*See Your Profile/i

export const youpornLoggedInPattern = /isLoggedInUser\s*=\s*true/i
export const youpornLoggedOutPattern = /isLoggedInUser\s*=\s*false/i
export const youpornUsernamePattern = /liu_username\s*=\s*'([^']*)'/i
export const youpornProfileLinkPattern = /href="\/users\/([^"/?#]+)"/i

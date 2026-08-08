import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const __filename = fileURLToPath(import.meta.url)
export const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')

export const APP_NAME = 'Squirrel'
export const APP_ID = 'com.klaxon.squirrel.desktop'
export const APP_ICON_PATH = path.join(__dirname, 'assets', 'icon.png')
export const DEFAULT_APP_URL = 'http://127.0.0.1:8001'
export const SERVER_CONFIG_FILE = 'server-config.json'

export const desktopChromeVersion = process.versions.chrome || '124.0.0.0'
export const desktopChromeMajorVersion = desktopChromeVersion.split('.')[0] || '124'
export const desktopChromeUserAgent = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${desktopChromeVersion} Safari/537.36`
export const androidMobileChromeUserAgent = `Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${desktopChromeVersion} Mobile Safari/537.36`

/**
 * FreeTube (`src/main/index.js`): strip Electron / product-name tokens from the
 * Chromium session UA. googlevideo videoplayback often 403s when the request
 * advertises `Electron/x.y.z` — official Chrome UA is required for segment
 * fetches (including Shaka alr redirect follow-ups).
 */
export const stripElectronFromUserAgent = (userAgent, productName = APP_NAME) => {
  const productToken = String(productName || '').trim().toLowerCase()
  return String(userAgent || '')
    .split(/\s+/)
    .filter((part) => {
      if (!part) return false
      const normalizedPart = part.toLowerCase()
      if (normalizedPart.startsWith('electron/')) return false
      if (
        productToken
        && (normalizedPart === productToken || normalizedPart.startsWith(`${productToken}/`))
      ) return false
      return true
    })
    .join(' ')
}

export const youtubeOAuthStateFilePath = path.join(repoRoot, 'config', 'youtube_oauth.json')

/**
 * Backend-synced bilibili cookies (Netscape cookies.txt format, written by the
 * backend's CookieCloud import at config/site_cookies/bilibili.txt). The
 * desktop reads this file as a fallback when the Electron session has no
 * bilibili SESSDATA, so playurl/media requests resolve with the browser login.
 * Overridable at runtime via the BILIBILI_COOKIE_FILE env var.
 */
export const bilibiliCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'bilibili.txt')

export const SITE_SESSION_STORAGE_TYPES = [
  'cookies',
  'filesystem',
  'indexdb',
  'localstorage',
  'serviceworkers',
  'cachestorage',
  'websql',
]

export const CACHE_TTL_MS = 5 * 60 * 1000

export const DOCUMENT_READ_TIMEOUT_MS = 10000

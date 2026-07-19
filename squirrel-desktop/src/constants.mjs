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

export const youtubeOAuthStateFilePath = path.join(repoRoot, 'config', 'youtube_oauth.json')

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

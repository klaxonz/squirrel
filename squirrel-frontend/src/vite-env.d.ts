/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface DesktopAppBridge {
  isDesktop?: boolean
  platform?: string
  versions?: {
    electron?: string
    chrome?: string
    node?: string
  }
  getWindowState?: () => Promise<DesktopWindowState>
  minimizeWindow?: () => Promise<DesktopWindowState>
  toggleMaximizeWindow?: () => Promise<DesktopWindowState>
  closeWindow?: () => Promise<DesktopWindowState>
  onWindowStateChange?: (listener: (state: DesktopWindowState) => void) => () => void
  reloadApp?: () => void
  openExternal?: (targetUrl: string) => Promise<boolean>
  resolveBilibiliPlayback?: DesktopPlaybackResolver
  resolvePornhubPlayback?: DesktopPlaybackResolver
  resolveYouPornPlayback?: DesktopPlaybackResolver
  resolveYouTubePlayback?: DesktopPlaybackResolver
  resolveYouTubeSubtitles?: DesktopSubtitleResolver
  getSiteLoginStatus?: (siteName: string) => Promise<DesktopSiteLoginStatus>
  openSiteLogin?: (siteName: string) => Promise<DesktopSiteLoginStatus>
  clearSiteSession?: (siteName: string) => Promise<DesktopSiteLoginStatus>
  getServerUrl?: () => Promise<string>
  setServerUrl?: (url: string) => Promise<string | false>
  clearServerUrl?: () => Promise<boolean>
  onServerUrlChange?: (listener: (url: string) => void) => () => void
}

type DesktopPlaybackResolver = (
  targetUrl: string,
  options?: { forceRefresh?: boolean }
) => Promise<{
  stream_type?: 'hls' | 'dash' | 'progressive'
  mpd_url?: string | null
  mpd_content?: string | null
  video_url?: string | null
  audio_url?: string | null
  default_quality_id?: string | null
  supports_manual_quality?: boolean
  qualities?: Array<{
    value: string
    label: string
    height?: number | null
    bandwidth?: number | null
    codec?: string
    id?: string | number | null
  }> | null
}>

type DesktopSubtitleResolver = (
  targetUrl: string,
  options?: { lang?: string; format?: 'vtt' }
) => Promise<{
  content: string
  format?: string | null
  language_code?: string | null
  language_name?: string | null
  translated?: boolean
  kind?: string | null
}>

interface DesktopSiteLoginStatus {
  site_name: string
  supported: boolean
  logged_in: boolean
  message: string
  checked_at: string
  source: 'desktop'
  cookie_count: number
  oauth_status?: string
  oauth_account?: {
    name?: string | null
    email?: string | null
    avatar?: string | null
  } | null
  verification_url?: string | null
  user_code?: string | null
}

interface DesktopWindowState {
  isMaximized?: boolean
}

interface Window {
  desktopApp?: DesktopAppBridge
}

// 扩展 Document 接口以支持各浏览器的全屏 API
interface Document {
  webkitFullscreenElement?: Element
  mozFullScreenElement?: Element
  msFullscreenElement?: Element
  webkitExitFullscreen?: () => Promise<void>
  mozCancelFullScreen?: () => Promise<void>
  msExitFullscreen?: () => Promise<void>
}

// 扩展 HTMLElement 接口以支持各浏览器的全屏 API
interface HTMLElement {
  webkitRequestFullscreen?: () => Promise<void>
  mozRequestFullScreen?: () => Promise<void>
  msRequestFullscreen?: () => Promise<void>
}

// Navigator 扩展
interface Navigator {
  connection?: {
    saveData?: boolean
    effectiveType?: string
    downlink?: number
  }
}

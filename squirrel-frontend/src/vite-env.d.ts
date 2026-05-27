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
  resolveJavdbPlayback?: DesktopPlaybackResolver
  resolveJavdbMetadata?: (targetUrl: string) => Promise<DesktopVideoMetadata>
  resolvePornhubPlayback?: DesktopPlaybackResolver
  resolveYouPornPlayback?: DesktopPlaybackResolver
  resolveYouTubePlayback?: DesktopPlaybackResolver
  resolveYouTubeSubtitles?: DesktopSubtitleResolver
  searchRemoteVideos?: DesktopRemoteSearchResolver
  getRemoteChannel?: DesktopRemoteChannelResolver
  getYouPornProfileAvatar?: (profileUrl: string) => Promise<string>
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
  options?: { forceRefresh?: boolean; title?: string; videoNo?: string }
) => Promise<{
  stream_type?: 'hls' | 'dash' | 'progressive'
  mpd_url?: string | null
  mpd_content?: string | null
  video_url?: string | null
  audio_url?: string | null
  default_quality_id?: string | null
  supports_manual_quality?: boolean
  metadata?: Record<string, unknown>
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

type DesktopVideoMetadata = {
  title?: string | null
  thumbnail?: string | null
  duration?: number | null
  publish_date?: string | null
  actors?: Array<{
    id?: string | number | null
    type?: string | null
    name: string
    url?: string | null
    avatar?: string | null
    is_nsfw?: boolean | null
  }>
}

type DesktopRemoteSearchResolver = (
  options: {
    query: string
    site?: string
    limit?: number
    page?: number
  }
) => Promise<{
  items: Array<{
    source: 'remote'
    site: string
    id?: string | number | null
    title: string
    url: string
    thumbnail?: string | null
    duration?: number | null
    publish_date?: string | null
    published_text?: string | null
    uploader?: string | null
    uploader_url?: string | null
    uploader_avatar?: string | null
    subscriptions?: Array<{
      id?: string | number | null
      type?: string | null
      name: string
      url?: string | null
      avatar?: string | null
      is_nsfw?: boolean | null
    }>
    actors?: Array<{
      id?: string | number | null
      type?: string | null
      name: string
      url?: string | null
      avatar?: string | null
      is_nsfw?: boolean | null
    }>
    description?: string | null
  }>
  errors?: string[]
  sites?: string[]
  page?: number
  has_more?: boolean
}>

type DesktopRemoteChannelResolver = (
  options: {
    site: string
    url: string
    limit?: number
    page?: number
    cursor?: unknown
    profile?: {
      id?: string | number | null
      type?: string | null
      name?: string | null
      url?: string | null
      avatar?: string | null
      is_nsfw?: boolean | null
    }
  }
) => Promise<{
  site: string
  profile: {
    id?: string | number | null
    type?: string | null
    name: string
    url: string
    avatar?: string | null
    description?: string | null
    site?: string | null
    is_nsfw?: boolean | null
  }
  items: Awaited<ReturnType<DesktopRemoteSearchResolver>>['items']
  page?: number
  has_more?: boolean
  next_cursor?: unknown
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

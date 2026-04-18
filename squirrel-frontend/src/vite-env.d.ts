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
  getServerUrl?: () => Promise<string>
  setServerUrl?: (url: string) => Promise<string | false>
  clearServerUrl?: () => Promise<boolean>
  onServerUrlChange?: (listener: (url: string) => void) => () => void
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

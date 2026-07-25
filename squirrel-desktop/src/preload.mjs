import { contextBridge, ipcRenderer } from 'electron'

const createUnidirectionalListener = (channel) => {
  return (listener) => {
    if (typeof listener !== 'function') return () => {}
    const handleEvent = (_event, value) => listener(value)
    ipcRenderer.on(channel, handleEvent)
    return () => ipcRenderer.removeListener(channel, handleEvent)
  }
}

contextBridge.exposeInMainWorld('desktopApp', Object.freeze({
  isDesktop: true,
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  reloadApp: () => ipcRenderer.send('desktop:reload'),
  openExternal: (targetUrl) => ipcRenderer.invoke('desktop:open-external', targetUrl),
  openWebContent: (targetUrl) => ipcRenderer.invoke('desktop:open-web-content', targetUrl),
  probeFrameEmbeddability: (targetUrl) => ipcRenderer.invoke('desktop:probe-frame-embeddability', targetUrl),
  openInAppWebView: (payload) => ipcRenderer.invoke('desktop:in-app-web-view-open', payload),
  setInAppWebViewBounds: (bounds) => ipcRenderer.invoke('desktop:in-app-web-view-set-bounds', bounds),
  reloadInAppWebView: () => ipcRenderer.invoke('desktop:in-app-web-view-reload'),
  hideInAppWebView: () => ipcRenderer.invoke('desktop:in-app-web-view-hide'),
  resolveBilibiliPlayback: (targetUrl, options) => ipcRenderer.invoke('desktop:resolve-bilibili-playback', targetUrl, options),
  resolveBilibiliSubtitles: (targetUrl, options) => ipcRenderer.invoke('desktop:resolve-bilibili-subtitles', targetUrl, options),
  resolveYouTubePlayback: (targetUrl, options) => ipcRenderer.invoke('desktop:resolve-youtube-playback', targetUrl, options),
  resolveYouTubeSubtitles: (targetUrl, options) => ipcRenderer.invoke('desktop:resolve-youtube-subtitles', targetUrl, options),
  searchRemoteVideos: (options) => ipcRenderer.invoke('desktop:search-remote-videos', options),
  getRemoteChannel: (options) => ipcRenderer.invoke('desktop:get-remote-channel', options),
  callMusic: (operation, payload) => ipcRenderer.invoke('desktop:music', operation, payload),
  getSiteLoginStatus: (siteName) => ipcRenderer.invoke('desktop:get-site-login-status', siteName),
  openSiteLogin: (siteName) => ipcRenderer.invoke('desktop:open-site-login', siteName),
  clearSiteSession: (siteName) => ipcRenderer.invoke('desktop:clear-site-session', siteName),
  getWindowState: () => ipcRenderer.invoke('desktop:get-window-state'),
  minimizeWindow: () => ipcRenderer.invoke('desktop:window-action', 'minimize'),
  toggleMaximizeWindow: () => ipcRenderer.invoke('desktop:window-action', 'toggle-maximize'),
  closeWindow: () => ipcRenderer.invoke('desktop:window-action', 'close'),
  onWindowStateChange: createUnidirectionalListener('desktop:window-state'),

  // Server config
  getServerUrl: () => ipcRenderer.invoke('server:get-url'),
  setServerUrl: (url) => ipcRenderer.invoke('server:set-url', url),
  clearServerUrl: () => ipcRenderer.invoke('server:clear-url'),
  onServerUrlChange: createUnidirectionalListener('server:url-changed'),

  // Navigation: main process forwards native back/forward (mouse side buttons,
  // multimedia keys, etc.) into renderer so useNavigationHistory can answer
  // "is there anything to pop?" uniformly with on-page controls.
  onNavigate: createUnidirectionalListener('desktop:navigate'),
}))

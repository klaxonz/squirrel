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
  resolveBilibiliPlayback: (targetUrl, options) => ipcRenderer.invoke('desktop:resolve-bilibili-playback', targetUrl, options),
  resolveYouTubePlayback: (targetUrl, options) => ipcRenderer.invoke('desktop:resolve-youtube-playback', targetUrl, options),
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
}))

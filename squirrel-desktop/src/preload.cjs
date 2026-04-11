const { contextBridge, ipcRenderer } = require('electron')

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
  getWindowState: () => ipcRenderer.invoke('desktop:get-window-state'),
  minimizeWindow: () => ipcRenderer.invoke('desktop:window-action', 'minimize'),
  toggleMaximizeWindow: () => ipcRenderer.invoke('desktop:window-action', 'toggle-maximize'),
  closeWindow: () => ipcRenderer.invoke('desktop:window-action', 'close'),
  onWindowStateChange: (listener) => {
    if (typeof listener !== 'function') {
      return () => {}
    }

    const handleWindowStateChange = (_event, value) => {
      listener(value)
    }

    ipcRenderer.on('desktop:window-state', handleWindowStateChange)
    return () => {
      ipcRenderer.removeListener('desktop:window-state', handleWindowStateChange)
    }
  },
}))

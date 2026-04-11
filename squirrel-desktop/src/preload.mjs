import { contextBridge, ipcRenderer } from 'electron'

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
}))

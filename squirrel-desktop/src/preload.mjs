import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('desktopApp', Object.freeze({
  isDesktop: true,
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
}))

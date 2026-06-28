import { ipcMain } from 'electron'
import { callDesktopMusic } from './music/service.mjs'

export const installMusicHandlers = () => {
  ipcMain.removeHandler('desktop:music')
  ipcMain.handle('desktop:music', async (_event, operation, payload = {}) => {
    if (typeof operation !== 'string' || !operation.trim()) {
      throw new Error('Invalid music operation')
    }
    return callDesktopMusic(operation, payload)
  })
}

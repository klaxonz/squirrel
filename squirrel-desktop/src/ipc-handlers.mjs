import { installPlaybackHandlers } from './ipc-playback.mjs'
import { installSearchHandlers } from './ipc-search.mjs'
import { installWindowHandlers } from './ipc-window.mjs'
import { installSiteLoginHandlers } from './ipc-site-login.mjs'
import { installServerConfigHandlers } from './ipc-server-config.mjs'
import { installMusicHandlers } from './ipc-music.mjs'

export const installDesktopBridgeHandlers = () => {
  installPlaybackHandlers()
  installSearchHandlers()
  installWindowHandlers()
  installSiteLoginHandlers()
  installServerConfigHandlers()
  installMusicHandlers()
}

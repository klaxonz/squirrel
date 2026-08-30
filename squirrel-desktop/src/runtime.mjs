import { session } from 'electron'
import { prewarmPlaybackProviders, PREWARM_KEEP_WARM_INTERVAL_MS } from './playback/providers/index.mjs'
import { installDesktopMediaHeaders } from './media-headers.mjs'

export const initializeDesktopRuntime = () => {
  const cleanupMediaHeaders = installDesktopMediaHeaders()
  const warmupTimer = setInterval(() => {
    void prewarmPlaybackProviders()
  }, PREWARM_KEEP_WARM_INTERVAL_MS)

  session.defaultSession.clearCache().catch((error) => {
    console.debug('[squirrel-desktop] clearCache failed', error)
  })

  void prewarmPlaybackProviders()

  return () => {
    clearInterval(warmupTimer)
    cleanupMediaHeaders()
  }
}

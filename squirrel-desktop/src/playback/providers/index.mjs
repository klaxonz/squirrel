import { prewarmYouTubePlayback } from './youtube/index.mjs'

const PROVIDERS = [
  { name: 'youtube', prewarm: prewarmYouTubePlayback },
]

export const prewarmPlaybackProviders = () => {
  for (const provider of PROVIDERS) {
    if (typeof provider.prewarm === 'function') {
      provider.prewarm().catch((error) => {
        console.debug('[squirrel-desktop] provider prewarm skipped', error?.message || error)
      })
    }
  }
}

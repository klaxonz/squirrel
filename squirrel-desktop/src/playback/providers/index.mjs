import { prewarmYouTubePlayback } from './youtube/index.mjs'
import { loadDocumentHtmlWithBrowserWindow } from '../../document-loader.mjs'
import { prewarmJavdbCloudflare } from './javdb/index.mjs'

const PROVIDERS = [
  { name: 'youtube', prewarm: prewarmYouTubePlayback },
  { name: 'javdb', prewarm: () => prewarmJavdbCloudflare(loadDocumentHtmlWithBrowserWindow) },
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

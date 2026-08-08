import { prewarmYouTubePlayback } from './youtube/index.mjs'

const PROVIDERS = [
  { name: 'youtube', prewarm: prewarmYouTubePlayback },
]

const PREWARM_RETRY_DELAY_MS = 2000
const PREWARM_MAX_ATTEMPTS = 2
/** Re-arm the YouTube runtime (remote WEB session + BotGuard minter) so a
 *  play that lands after a cold session expired never pays the 2–16s rebuild
 *  inside the resolve path. Cheap when warm: session cache hit + fresh minter
 *  short-circuit immediately. */
export const PREWARM_KEEP_WARM_INTERVAL_MS = 15 * 60 * 1000

const warmProvider = async (provider, attempt = 1) => {
  try {
    await provider.prewarm()
    return { ok: true, provider: provider.name }
  } catch (error) {
    if (attempt < PREWARM_MAX_ATTEMPTS) {
      await new Promise((resolve) => setTimeout(resolve, PREWARM_RETRY_DELAY_MS))
      return warmProvider(provider, attempt + 1)
    }
    console.debug(
      `[squirrel-desktop] provider prewarm failed (${provider.name})`,
      error?.message || error,
    )
    return { ok: false, provider: provider.name }
  }
}

export const prewarmPlaybackProviders = () => {
  return Promise.all(PROVIDERS.map((provider) => warmProvider(provider)))
}

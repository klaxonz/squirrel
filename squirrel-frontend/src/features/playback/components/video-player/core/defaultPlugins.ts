import type { PluginConfig } from './types'

import { AnalyticsPlugin } from '../plugins/analytics'
import { SubtitlesPlugin } from '../plugins/subtitles'
import type { StreamAdapterOptions } from './engine-types'

export type DefaultPluginsOptions = {
  enableHls?: boolean
  enableDash?: boolean
  enableSubtitles?: boolean
  enableAnalytics?: boolean
}

/**
 * The non-stream plugins the player registers by default.
 *
 * Stream technology (HLS / dashjs / shaka) is no longer carried here: the engine
 * instantiates those adapters itself from `streamAdapters` (see docs/adr/0001).
 * This helper now returns only Subtitles + Analytics, which are genuine
 * lifecycle plugins driven by PluginManager's event forwarding.
 */
export const createDefaultPlayerPlugins = (options: DefaultPluginsOptions = {}): PluginConfig[] => {
  const {
    enableSubtitles = true,
    enableAnalytics = false
  } = options

  const plugins: PluginConfig[] = []

  if (enableSubtitles) {
    plugins.push({ plugin: () => new SubtitlesPlugin(), options: { autoLoad: false } })
  }

  if (enableAnalytics) {
    plugins.push({ plugin: () => new AnalyticsPlugin(), options: { debug: false, reportInterval: 30000 } })
  }

  return plugins
}

/**
 * The default stream-adapter configuration the engine uses. Mirrors the
 * enableHls / enableDash toggles that used to live on the plugin list; the
 * adapter option bags are left to the adapters' built-in defaults.
 */
export const createDefaultStreamAdapterOptions = (options: DefaultPluginsOptions = {}): StreamAdapterOptions => {
  const { enableHls = true, enableDash = true } = options
  return {
    enableHls,
    enableDash
  }
}

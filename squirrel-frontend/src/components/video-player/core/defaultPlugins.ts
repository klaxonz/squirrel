import type { PluginConfig } from './types'

import { AnalyticsPlugin } from '../plugins/analytics'
import { DashPlugin } from '../plugins/dash'
import { HlsPlugin } from '../plugins/hls'
import { ShakaDashPlugin } from '../plugins/shaka-dash'
import { SubtitlesPlugin } from '../plugins/subtitles'

export type DefaultPluginsOptions = {
  enableHls?: boolean
  enableDash?: boolean
  enableSubtitles?: boolean
  enableAnalytics?: boolean
}

export const createDefaultPlayerPlugins = (options: DefaultPluginsOptions = {}): PluginConfig[] => {
  const {
    enableHls = true,
    enableDash = true,
    enableSubtitles = true,
    enableAnalytics = false
  } = options

  const plugins: PluginConfig[] = []

  if (enableHls) {
    plugins.push({ plugin: () => new HlsPlugin() })
  }

  if (enableDash) {
    plugins.push({ plugin: () => new DashPlugin() })
    plugins.push({ plugin: () => new ShakaDashPlugin() })
  }

  if (enableSubtitles) {
    plugins.push({ plugin: () => new SubtitlesPlugin(), options: { autoLoad: false } })
  }

  if (enableAnalytics) {
    plugins.push({ plugin: () => new AnalyticsPlugin(), options: { debug: false, reportInterval: 30000 } })
  }

  return plugins
}

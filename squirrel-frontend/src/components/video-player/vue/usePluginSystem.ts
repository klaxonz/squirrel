/**
 * 插件系统 Vue Composable
 * 将插件系统集成到 Vue 播放器组件
 */

import { ref, shallowRef, onUnmounted, type Ref } from 'vue'
import { EventEmitter } from '../core/EventEmitter'
import { PluginManager } from '../core/PluginManager'
import { playerLogger } from '../core/logger'
import type {
  PlayerPlugin,
  PluginContext,
  PlayerEvents,
  PlayerState,
  PlayerError,
  MediaSource,
  QualityLevel
} from '../core/types'

export interface UsePluginSystemOptions {
  videoElement: Ref<HTMLVideoElement | null>
  onError?: (error: PlayerError) => void
}

export interface UsePluginSystemReturn {
  events: EventEmitter<PlayerEvents>
  pluginManager: PluginManager
  registerPlugin: (plugin: PlayerPlugin, options?: any) => Promise<void>
  unregisterPlugin: (name: string) => void
  setSource: (source: MediaSource) => void
  getPlugin: <T extends PlayerPlugin>(name: string) => T | null
  qualities: Ref<QualityLevel[]>
  currentQuality: Ref<string | null>
  setQuality: (quality: string | number) => void
  destroy: () => void
}

/**
 * 创建插件系统
 */
export function usePluginSystem({
  videoElement,
  onError
}: UsePluginSystemOptions): UsePluginSystemReturn {
  
  const events = new EventEmitter<PlayerEvents>()
  const pluginManager = new PluginManager(events)
  const logger = playerLogger
  
  const qualities = ref<QualityLevel[]>([])
  const currentQuality = ref<string | null>(null)
  const registeredQualityId = ref<number | null>(null)
  const currentSource = shallowRef<MediaSource | null>(null)

  // 创建插件上下文
  const createContext = (): PluginContext => ({
    get videoElement() {
      return videoElement.value
    },
    
    get state(): PlayerState {
      const video = videoElement.value
      return {
        playing: video ? !video.paused : false,
        paused: video?.paused ?? true,
        ended: video?.ended ?? false,
        waiting: false,
        seeking: video?.seeking ?? false,
        currentTime: video?.currentTime ?? 0,
        duration: video?.duration ?? 0,
        buffered: 0,
        volume: video?.volume ?? 1,
        muted: video?.muted ?? false,
        playbackRate: video?.playbackRate ?? 1,
        fullscreen: !!document.fullscreenElement,
        pip: document.pictureInPictureElement === video,
        quality: currentQuality.value,
        autoQuality: currentQuality.value === 'auto'
      }
    },

    logger,

    on: events.on.bind(events),
    off: events.off.bind(events),
    emit: events.emit.bind(events),
    once: events.once.bind(events),

    async play() {
      await videoElement.value?.play()
    },

    pause() {
      videoElement.value?.pause()
    },

    seek(time: number) {
      if (videoElement.value) {
        videoElement.value.currentTime = time
      }
    },

    setVolume(volume: number) {
      if (videoElement.value) {
        videoElement.value.volume = Math.max(0, Math.min(1, volume))
      }
    },

    setMuted(muted: boolean) {
      if (videoElement.value) {
        videoElement.value.muted = muted
      }
    },

    setPlaybackRate(rate: number) {
      if (videoElement.value) {
        videoElement.value.playbackRate = rate
      }
    },

    setQuality(quality: string | number) {
      // 遍历插件调用 setQuality
      pluginManager.getAll().forEach(plugin => {
        if ('setQuality' in plugin && typeof (plugin as any).setQuality === 'function') {
          (plugin as any).setQuality(quality)
        }
      })
      currentQuality.value = String(quality)
      events.emit('qualitychange', { quality: String(quality), auto: quality === 'auto' })
    },

    getQualities() {
      return qualities.value
    },

    registerQualities(newQualities: QualityLevel[]) {
      qualities.value = newQualities
      if (registeredQualityId.value !== null) {
        const match = newQualities.find((item) => item.id === registeredQualityId.value)
        if (match?.label) {
          currentQuality.value = match.label
        }
      }
    },

    registerCurrentQualityId(id?: number) {
      registeredQualityId.value = typeof id === 'number' ? id : null
      if (registeredQualityId.value === null) return
      const match = qualities.value.find((item) => item.id === registeredQualityId.value)
      if (match?.label) {
        currentQuality.value = match.label
      }
    },

    setSource(source: MediaSource) {
      currentSource.value = source
      events.emit('sourcechange', source)
    },

    getSource() {
      return currentSource.value
    },

    async requestFullscreen() {
      await videoElement.value?.requestFullscreen()
    },

    async exitFullscreen() {
      await document.exitFullscreen()
    },

    async requestPictureInPicture() {
      await videoElement.value?.requestPictureInPicture()
    },

    async exitPictureInPicture() {
      await document.exitPictureInPicture()
    },

    reportError(error: PlayerError) {
      events.emit('error', error)
      onError?.(error)
    },

    getPlugin<T extends PlayerPlugin>(name: string) {
      return pluginManager.get<T>(name)
    }
  })

  // 初始化上下文
  const context = createContext()
  pluginManager.setContext(context)

  /**
   * 注册插件
   */
  const registerPlugin = async (plugin: PlayerPlugin, options?: any): Promise<void> => {
    await pluginManager.register(plugin, options)
  }

  /**
   * 注销插件
   */
  const unregisterPlugin = (name: string): void => {
    pluginManager.unregister(name)
  }

  /**
   * 设置媒体源
   */
  const setSource = (source: MediaSource): void => {
    context.setSource(source)
  }

  /**
   * 获取插件
   */
  const getPlugin = <T extends PlayerPlugin>(name: string): T | null => {
    return pluginManager.get<T>(name)
  }

  /**
   * 设置质量
   */
  const setQuality = (quality: string | number): void => {
    context.setQuality(quality)
  }

  /**
   * 销毁
   */
  const destroy = (): void => {
    pluginManager.destroy()
    events.destroy()
  }

  // 组件卸载时自动销毁
  onUnmounted(() => {
    destroy()
  })

  return {
    events,
    pluginManager,
    registerPlugin,
    unregisterPlugin,
    setSource,
    getPlugin,
    qualities,
    currentQuality,
    setQuality,
    destroy
  }
}

export default usePluginSystem

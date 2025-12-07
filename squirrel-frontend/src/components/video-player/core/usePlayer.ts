/**
 * 集成播放器 Composable
 * 整合插件系统、主题、国际化、适配器等所有模块
 */

import { ref, computed, watch, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { usePlayerStore, type PlayerStore } from '../../../stores/playerStore'

// 核心模块
import { EventEmitter } from './EventEmitter'
import { PluginManager } from './PluginManager'
import { useErrorRecovery } from './useErrorRecovery'
import { useGestures } from './useGestures'
import { useA11y } from './useA11y'
import { usePlayerAdapter } from './usePlayerAdapter'
import { useControlsLayout } from './useControlsLayout'
import { useIcons } from './useIcons'
import type { PlayerEvents, PluginContext, PlayerState, QualityLevel, MediaSource, PlayerError } from './types'

// 插件
import { HlsPlugin } from '../plugins/hls'
import { DashPlugin } from '../plugins/dash'
import { SubtitlesPlugin, type SubtitleTrack } from '../plugins/subtitles'
import { AnalyticsPlugin } from '../plugins/analytics'

// 主题
import { useTheme, type ThemeName } from '../themes'

// 国际化
import { useI18n } from '../i18n'

// 类型
import type { VideoInfo, QualityOption } from '../../../types/video-player'

export interface PlayerOptions {
  // 初始配置
  autoplay?: boolean
  muted?: boolean
  volume?: number
  loop?: boolean
  
  // 主题
  theme?: ThemeName
  
  // 语言
  locale?: string
  
  // 插件配置
  enableHls?: boolean
  enableDash?: boolean
  enableSubtitles?: boolean
  enableAnalytics?: boolean
  
  // 手势
  enableGestures?: boolean
  
  // 适配器
  useApiAdapter?: boolean
  apiBaseUrl?: string
  
  // 回调
  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onError?: (error: PlayerError) => void
  onTimeUpdate?: (time: number) => void
  onQualityChange?: (quality: string) => void
}

export interface PlayerReturn {
  // Store
  store: PlayerStore
  
  // DOM refs
  videoElement: Ref<HTMLVideoElement | null>
  containerElement: Ref<HTMLElement | null>
  
  // 状态
  isReady: Ref<boolean>
  isPlaying: ComputedRef<boolean>
  isPaused: ComputedRef<boolean>
  currentTime: ComputedRef<number>
  duration: ComputedRef<number>
  volume: ComputedRef<number>
  isMuted: ComputedRef<boolean>
  isFullscreen: ComputedRef<boolean>
  qualities: Ref<QualityLevel[]>
  currentQuality: Ref<string | null>
  
  // 流类型检测
  isHlsStream: ComputedRef<boolean>
  isDashStream: ComputedRef<boolean>
  
  // 控制方法
  play: () => Promise<void>
  pause: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  toggleMute: () => void
  setPlaybackRate: (rate: number) => void
  setQuality: (quality: string) => void
  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>
  
  // 字幕
  subtitleTracks: Ref<SubtitleTrack[]>
  currentSubtitle: Ref<SubtitleTrack | null>
  setSubtitle: (track: SubtitleTrack | null) => void
  toggleSubtitles: () => void
  
  // 源管理
  loadSource: (video: VideoInfo) => void
  
  // 主题
  theme: Ref<ThemeName>
  setTheme: (theme: ThemeName) => void
  
  // 国际化
  t: (key: string, params?: Record<string, any>) => string
  locale: Ref<string>
  setLocale: (locale: string) => void
  
  // 适配器
  saveProgress: () => void
  loadProgress: (videoId: string) => Promise<number | null>
  
  // 无障碍
  announce: (message: string) => void
  
  // 插件
  getPlugin: <T>(name: string) => T | null
  
  // 事件
  on: EventEmitter<PlayerEvents>['on']
  off: EventEmitter<PlayerEvents>['off']
  
  // 布局
  controlsLayout: ReturnType<typeof useControlsLayout>
  
  // 图标
  icons: ReturnType<typeof useIcons>
  
  // 销毁
  destroy: () => void
}

/**
 * 集成播放器 Composable
 */
export function usePlayer(options: PlayerOptions = {}): PlayerReturn {
  const {
    autoplay = false,
    muted = false,
    volume = 100,
    loop = false,
    theme: initialTheme = 'dark',
    locale: initialLocale,
    enableHls = true,
    enableDash = true,
    enableSubtitles = true,
    enableAnalytics = false,
    enableGestures = true,
    onPlay,
    onPause,
    onEnded,
    onError,
    onTimeUpdate,
    onQualityChange
  } = options

  // ===== 基础状态 =====
  const store = usePlayerStore()
  const videoElement = ref<HTMLVideoElement | null>(null)
  const containerElement = ref<HTMLElement | null>(null)
  const isReady = ref(false)
  const qualities = ref<QualityLevel[]>([])
  const currentQuality = ref<string | null>(null)
  const subtitleTracks = ref<SubtitleTrack[]>([])
  const currentSubtitle = ref<SubtitleTrack | null>(null)
  const currentVideo = ref<VideoInfo | null>(null)

  // ===== 事件系统 =====
  const events = new EventEmitter<PlayerEvents>()
  const pluginManager = new PluginManager(events)

  // ===== 主题 =====
  const { theme, setTheme: applyTheme, isDark } = useTheme({ defaultTheme: initialTheme })
  const setTheme = (newTheme: ThemeName) => {
    applyTheme(newTheme)
  }

  // ===== 国际化 =====
  const { t, locale, setLocale } = useI18n({ locale: initialLocale as any })

  // ===== 适配器 =====
  const { config, saveProgress: adapterSaveProgress, loadProgress: adapterLoadProgress } = usePlayerAdapter({
    autoLoadConfig: true
  })

  // ===== 控制栏布局 =====
  const controlsLayout = useControlsLayout({ layout: 'default' })

  // ===== 图标 =====
  const icons = useIcons()

  // ===== 错误恢复 =====
  const { handleError: handleRecoveryError, setQualities: setRecoveryQualities } = useErrorRecovery({
    maxRetries: 3,
    enableQualityFallback: true,
    onQualityFallback: (quality) => {
      setQuality(quality.label)
    },
    onRecoveryFailed: (error) => {
      onError?.(error)
    }
  })

  // ===== 计算属性 =====
  const isPlaying = computed(() => store.playing)
  const isPaused = computed(() => !store.playing)
  const currentTime = computed(() => store.currentTime)
  const duration = computed(() => store.duration)
  const volumeValue = computed(() => store.volume)
  const isMuted = computed(() => store.muted)
  const isFullscreen = computed(() => store.fullscreen)

  const isHlsStream = computed(() => {
    const url = currentVideo.value?.stream_video_url
    return !!url && url.includes('.m3u8')
  })

  const isDashStream = computed(() => {
    const video = currentVideo.value as any
    return !!video?.mpd_url || (!!video?.stream_video_url && video.stream_video_url.endsWith('.mpd'))
  })

  // ===== 插件上下文 =====
  const createPluginContext = (): PluginContext => ({
    get videoElement() { return videoElement.value },
    get state(): PlayerState {
      return {
        playing: store.playing,
        paused: !store.playing,
        ended: false,
        waiting: store.loading,
        seeking: store.seekingVideo,
        currentTime: store.currentTime,
        duration: store.duration,
        buffered: store.bufferedPercent,
        volume: store.volume / 100,
        muted: store.muted,
        playbackRate: store.playbackRate,
        fullscreen: store.fullscreen,
        pip: store.pip,
        quality: currentQuality.value,
        autoQuality: currentQuality.value === 'auto'
      }
    },
    on: events.on.bind(events),
    off: events.off.bind(events),
    emit: events.emit.bind(events),
    once: events.once.bind(events),
    async play() { await play() },
    pause() { pause() },
    seek(time) { seek(time) },
    setVolume(v) { setVolume(v * 100) },
    setMuted(m) { store.setMuted(m) },
    setPlaybackRate(r) { setPlaybackRate(r) },
    setQuality(q) { setQuality(String(q)) },
    getQualities() { return qualities.value },
    registerQualities(qs) {
      qualities.value = qs
      setRecoveryQualities(qs)
    },
    setSource(source) { /* handled by loadSource */ },
    getSource() { return currentVideo.value ? { src: (currentVideo.value as any).stream_video_url || '' } : null },
    async requestFullscreen() { await toggleFullscreen() },
    async exitFullscreen() { if (store.fullscreen) await toggleFullscreen() },
    async requestPictureInPicture() { await togglePictureInPicture() },
    async exitPictureInPicture() { if (store.pip) await togglePictureInPicture() },
    reportError(error) {
      events.emit('error', error)
      onError?.(error)
    },
    getPlugin<T>(name: string) { return pluginManager.get(name) as T }
  })

  // ===== 控制方法 =====
  const play = async (): Promise<void> => {
    if (!videoElement.value) return
    try {
      await videoElement.value.play()
      store.setPlaying(true)
      events.emit('play', undefined)
      onPlay?.()
    } catch (e) {
      console.warn('[IntegratedPlayer] Play failed:', e)
    }
  }

  const pause = (): void => {
    if (!videoElement.value) return
    videoElement.value.pause()
    store.setPlaying(false)
    events.emit('pause', undefined)
    onPause?.()
  }

  const seek = (time: number): void => {
    if (!videoElement.value) return
    videoElement.value.currentTime = time
    store.setCurrentTime(time)
    events.emit('seeking', time)
  }

  const setVolume = (vol: number): void => {
    const v = Math.max(0, Math.min(100, vol))
    store.setVolume(v)
    if (videoElement.value) {
      videoElement.value.volume = v / 100
    }
    events.emit('volumechange', { volume: v / 100, muted: store.muted })
  }

  const toggleMute = (): void => {
    store.toggleMute()
    if (videoElement.value) {
      videoElement.value.muted = store.muted
    }
    events.emit('volumechange', { volume: store.volume / 100, muted: store.muted })
  }

  const setPlaybackRate = (rate: number): void => {
    store.setPlaybackRate(rate)
    if (videoElement.value) {
      videoElement.value.playbackRate = rate
    }
    events.emit('ratechange', rate)
  }

  const setQuality = (quality: string): void => {
    currentQuality.value = quality
    store.setCurrentQuality(quality)
    
    // 通知插件
    const hlsPlugin = pluginManager.get<HlsPlugin>('hls')
    const dashPlugin = pluginManager.get<DashPlugin>('dash')
    
    if (hlsPlugin && isHlsStream.value) {
      hlsPlugin.setQuality(quality)
    } else if (dashPlugin && isDashStream.value) {
      dashPlugin.setQuality(quality)
    }
    
    events.emit('qualitychange', { quality, auto: quality === 'auto' })
    onQualityChange?.(quality)
  }

  const toggleFullscreen = async (): Promise<void> => {
    if (!containerElement.value) return
    
    try {
      if (!document.fullscreenElement) {
        await containerElement.value.requestFullscreen()
        store.setFullscreen(true)
      } else {
        await document.exitFullscreen()
        store.setFullscreen(false)
      }
      events.emit('fullscreenchange', store.fullscreen)
    } catch (e) {
      console.warn('[IntegratedPlayer] Fullscreen failed:', e)
    }
  }

  const togglePictureInPicture = async (): Promise<void> => {
    if (!videoElement.value) return
    
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture()
        store.setPip(false)
      } else {
        await videoElement.value.requestPictureInPicture()
        store.setPip(true)
      }
    } catch (e) {
      console.warn('[IntegratedPlayer] PiP failed:', e)
    }
  }

  // ===== 字幕 =====
  const setSubtitle = (track: SubtitleTrack | null): void => {
    currentSubtitle.value = track
    const subtitlesPlugin = pluginManager.get<SubtitlesPlugin>('subtitles')
    
    if (subtitlesPlugin) {
      if (track) {
        subtitlesPlugin.loadTrack(track)
        subtitlesPlugin.enable()
      } else {
        subtitlesPlugin.disable()
      }
    }
    
    store.setCurrentSubtitle(track as any)
    store.setSubtitlesEnabled(!!track)
  }

  const toggleSubtitles = (): void => {
    const subtitlesPlugin = pluginManager.get<SubtitlesPlugin>('subtitles')
    if (subtitlesPlugin) {
      subtitlesPlugin.toggle()
      store.setSubtitlesEnabled(subtitlesPlugin.isEnabled())
    }
  }

  // ===== 源加载 =====
  const loadSource = (video: VideoInfo): void => {
    currentVideo.value = video
    
    // 设置字幕轨道
    if (video.subtitles && enableSubtitles) {
      const tracks: SubtitleTrack[] = video.subtitles.map((s, i) => ({
        id: s.id || `sub-${i}`,
        label: s.label || s.language || `Subtitle ${i + 1}`,
        language: s.language || 'unknown',
        url: s.url,
        default: i === 0
      }))
      subtitleTracks.value = tracks
      
      const subtitlesPlugin = pluginManager.get<SubtitlesPlugin>('subtitles')
      if (subtitlesPlugin) {
        subtitlesPlugin.setTracks(tracks)
      }
    }
    
    // 通知插件源变化
    const src = (video as any).stream_video_url || (video as any).mpd_url || ''
    const sourceType = isHlsStream.value ? 'hls' : (isDashStream.value ? 'dash' : 'native')
    
    events.emit('sourcechange', { src, type: sourceType })
  }

  // ===== 进度管理 =====
  const saveProgress = (): void => {
    if (!currentVideo.value?.id) return
    adapterSaveProgress(currentVideo.value.id, store.currentTime, store.duration)
  }

  const loadProgress = async (videoId: string): Promise<number | null> => {
    const progress = await adapterLoadProgress(videoId)
    return progress?.currentTime ?? null
  }

  // ===== 无障碍 =====
  const { announce } = useA11y({
    videoElement,
    containerElement
  })

  // ===== 手势 =====
  if (enableGestures) {
    useGestures({
      element: containerElement,
      callbacks: {
        onSeek: (delta) => {
          const newTime = Math.max(0, Math.min(store.duration, store.currentTime + delta))
          seek(newTime)
        },
        onVolumeChange: (delta) => {
          setVolume(store.volume + delta)
        },
        onDoubleTapLeft: () => {
          seek(Math.max(0, store.currentTime - 10))
          announce(t('skipBackward'))
        },
        onDoubleTapRight: () => {
          seek(Math.min(store.duration, store.currentTime + 10))
          announce(t('skipForward'))
        },
        onDoubleTapCenter: () => {
          if (store.playing) {
            pause()
          } else {
            play()
          }
        }
      }
    })
  }

  // ===== 初始化插件 =====
  const initPlugins = async (): Promise<void> => {
    const context = createPluginContext()
    pluginManager.setContext(context)

    // HLS 插件
    if (enableHls) {
      await pluginManager.register(new HlsPlugin(), {
        onBandwidthSample: (loaded, duration) => {
          // 可以更新性能状态
        }
      })
    }

    // DASH 插件
    if (enableDash) {
      await pluginManager.register(new DashPlugin())
    }

    // 字幕插件
    if (enableSubtitles) {
      await pluginManager.register(new SubtitlesPlugin(), {
        autoLoad: true
      })
    }

    // 分析插件
    if (enableAnalytics) {
      await pluginManager.register(new AnalyticsPlugin(), {
        debug: false,
        reportInterval: 30000
      })
    }

    isReady.value = true
  }

  // ===== 事件监听 =====
  const setupVideoListeners = (): void => {
    if (!videoElement.value) return

    const video = videoElement.value

    video.addEventListener('play', () => {
      store.setPlaying(true)
      events.emit('play', undefined)
      onPlay?.()
    })

    video.addEventListener('pause', () => {
      store.setPlaying(false)
      events.emit('pause', undefined)
      onPause?.()
    })

    video.addEventListener('ended', () => {
      events.emit('ended', undefined)
      onEnded?.()
    })

    video.addEventListener('timeupdate', () => {
      store.setCurrentTime(video.currentTime)
      events.emit('timeupdate', { currentTime: video.currentTime, duration: video.duration })
      onTimeUpdate?.(video.currentTime)
    })

    video.addEventListener('durationchange', () => {
      store.setDuration(video.duration)
      events.emit('durationchange', video.duration)
    })

    video.addEventListener('volumechange', () => {
      store.setVolume(video.volume * 100)
      store.setMuted(video.muted)
    })

    video.addEventListener('waiting', () => {
      store.setLoading(true, 'buffering')
      events.emit('waiting', undefined)
    })

    video.addEventListener('canplay', () => {
      store.setLoading(false, 'ready')
      store.setCanPlay('video', true)
      events.emit('canplay', undefined)
    })

    video.addEventListener('error', (e) => {
      const error: PlayerError = {
        code: 'MEDIA_ERROR',
        message: 'Video playback error',
        fatal: true,
        details: e
      }
      handleRecoveryError(error)
      events.emit('error', error)
      onError?.(error)
    })
  }

  // ===== 全屏监听 =====
  const handleFullscreenChange = (): void => {
    const isFs = !!document.fullscreenElement
    store.setFullscreen(isFs)
    events.emit('fullscreenchange', isFs)
  }

  // ===== 生命周期 =====
  onMounted(async () => {
    // 应用初始配置
    store.setAutoplay(autoplay)
    store.setMuted(muted)
    store.setVolume(volume)
    store.setLoop(loop)

    // 应用适配器配置
    if (config.value.volume !== undefined) store.setVolume(config.value.volume)
    if (config.value.muted !== undefined) store.setMuted(config.value.muted)
    if (config.value.playbackRate !== undefined) store.setPlaybackRate(config.value.playbackRate)

    // 初始化插件
    await initPlugins()

    // 监听全屏变化
    document.addEventListener('fullscreenchange', handleFullscreenChange)

    // 设置视频监听
    if (videoElement.value) {
      setupVideoListeners()
    }
  })

  onUnmounted(() => {
    // 保存进度
    saveProgress()

    // 清理
    document.removeEventListener('fullscreenchange', handleFullscreenChange)
    pluginManager.destroy()
    events.destroy()
  })

  // 监听 videoElement 变化
  watch(videoElement, (el) => {
    if (el) {
      setupVideoListeners()
    }
  })

  // ===== 销毁 =====
  const destroy = (): void => {
    saveProgress()
    pluginManager.destroy()
    events.destroy()
  }

  return {
    store,
    videoElement,
    containerElement,
    isReady,
    isPlaying,
    isPaused,
    currentTime,
    duration,
    volume: volumeValue,
    isMuted,
    isFullscreen,
    qualities,
    currentQuality,
    isHlsStream,
    isDashStream,
    play,
    pause,
    seek,
    setVolume,
    toggleMute,
    setPlaybackRate,
    setQuality,
    toggleFullscreen,
    togglePictureInPicture,
    subtitleTracks,
    currentSubtitle,
    setSubtitle,
    toggleSubtitles,
    loadSource,
    theme,
    setTheme,
    t,
    locale,
    setLocale,
    saveProgress,
    loadProgress,
    announce,
    getPlugin: <T>(name: string) => pluginManager.get(name) as T,
    on: events.on.bind(events),
    off: events.off.bind(events),
    controlsLayout,
    icons,
    destroy
  }
}

export default usePlayer

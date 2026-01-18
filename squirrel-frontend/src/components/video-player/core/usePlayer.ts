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
import { useI18n, type LocaleCode, type LocaleMessages } from '../i18n'

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
  locale?: LocaleCode
  
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
  
  // 视频上下文
  video?: Ref<VideoInfo | null | undefined>
  
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
  currentQualityLabel: Ref<string | null>
  currentQualityId: Ref<number | null>
  
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
  setQuality: (quality: string | number) => void
  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>
  
  // 字幕
  subtitleTracks: Ref<SubtitleTrack[]>
  currentSubtitle: Ref<SubtitleTrack | null>
  setSubtitle: (track: SubtitleTrack | null) => void
  setSubtitleTracks: (tracks: SubtitleTrack[]) => void
  toggleSubtitles: () => void
  
  // 源管理（通用 API）
  loadSource: (source: MediaSource) => void
  
  // 主题
  theme: Ref<ThemeName>
  setTheme: (theme: ThemeName) => void
  
  // 国际化
  t: (key: keyof LocaleMessages, params?: Record<string, string | number>) => string
  locale: Ref<LocaleCode>
  setLocale: (locale: LocaleCode) => void
  
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
    video,
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
  const currentQualityLabel = ref<string | null>(null)
  const currentQualityId = ref<number | null>(null)
  const registeredQualityId = ref<number | null>(null)

  const subtitleTracks = ref<SubtitleTrack[]>([])
  const currentSubtitle = ref<SubtitleTrack | null>(null)
  const currentVideo = ref<VideoInfo | null>(null)

  if (video) {
    watch(video, (nextVideo) => {
      currentVideo.value = (nextVideo as VideoInfo) || null
    }, { immediate: true })
  }

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
  const {
    config,
    loadConfig: adapterLoadConfig,
    saveConfig: adapterSaveConfig,
    saveProgress: adapterSaveProgress,
    loadProgress: adapterLoadProgress
  } = usePlayerAdapter({
    autoLoadConfig: false
  })


  // ===== 控制栏布局 =====
  const controlsLayout = useControlsLayout({ layout: 'default' })

  // ===== 图标 =====
  const icons = useIcons()

  // ===== 错误恢复 =====
  const reportFatalError = (error: PlayerError): void => {
    store.setLoading(false, 'idle')
    store.setPlaying(false)
    events.emit('error', error)
    onError?.(error)
  }

  const { handleError: handleRecoveryError, setQualities: setRecoveryQualities } = useErrorRecovery({
    maxRetries: 3,
    enableQualityFallback: true,
    onQualityFallback: (quality) => {
      setQuality(quality.label)
    }
  })


  // ===== 计算属性 =====
  // 注意：Pinia 会自动解包 setup store 的 ref，直接访问即可
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
        buffered: store.bufferedProgress,
        volume: store.volume / 100,
        muted: store.muted,
        playbackRate: store.playbackRate,
        fullscreen: store.fullscreen,
        pip: store.pictureInPicture,
        quality: currentQualityLabel.value,
        autoQuality: currentQualityLabel.value === 'auto'

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
    setQuality(q) { setQuality(q) },
    getQualities() { return qualities.value },
    registerQualities(qs) {
      qualities.value = qs
      setRecoveryQualities(qs)
      if (registeredQualityId.value !== null) {
        const match = qs.find((item) => item.id === registeredQualityId.value)
        if (match?.label) {
          currentQualityLabel.value = match.label
          store.setCurrentQuality(match.label, registeredQualityId.value)
          currentQualityId.value = registeredQualityId.value
        }
      }
    },
    registerCurrentQualityId(id?: number) {
      registeredQualityId.value = typeof id === 'number' ? id : null
      if (registeredQualityId.value === null) return
      const match = qualities.value.find((item) => item.id === registeredQualityId.value)
      if (match?.label) {
        currentQualityLabel.value = match.label
        store.setCurrentQuality(match.label, registeredQualityId.value)
        currentQualityId.value = registeredQualityId.value
      } else {
        currentQualityId.value = registeredQualityId.value
      }
    },
    setSource(source) { /* handled by loadSource */ },
    getSource() {
      if (currentVideo.value) {
        return {
          src: (currentVideo.value as any).mpd_url ||
            (currentVideo.value as any).stream_video_url ||
            ''
        }
      }
      return null
    },
    async requestFullscreen() { await toggleFullscreen() },
    async exitFullscreen() { if (store.fullscreen) await toggleFullscreen() },
    async requestPictureInPicture() { await togglePictureInPicture() },
    async exitPictureInPicture() { if (store.pictureInPicture) await togglePictureInPicture() },
    reportError(error) {
      reportFatalError(error)
    },

    getPlugin<T>(name: string) { return pluginManager.get(name) as T }
  })

  // ===== 控制方法 =====
  // 注意：状态由视频元素的原生事件驱动，这里只负责调用原生方法
  const play = async (): Promise<void> => {
    if (!videoElement.value) return
    try {
      await videoElement.value.play()
      // 状态由 'play' 事件更新
    } catch (e) {
      console.warn('[usePlayer] Play failed:', e)
    }
  }

  const pause = (): void => {
    if (!videoElement.value) return
    videoElement.value.pause()
    // 状态由 'pause' 事件更新
  }

  const seek = (time: number): void => {
    if (!videoElement.value) return
    videoElement.value.currentTime = time
    store.setCurrentTime(time)
    events.emit('seeking', time)
  }

  const setVolume = (vol: number): void => {
    const v = Math.max(0, Math.min(100, vol))
    const shouldUnmute = v > 0 && store.muted

    store.setVolume(v)
    if (shouldUnmute) {
      store.setMuted(false)
    }

    if (videoElement.value) {
      videoElement.value.volume = v / 100
      if (shouldUnmute) {
        videoElement.value.muted = false
      }
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

  const syncMediaElementSettings = (el: HTMLVideoElement | null): void => {
    if (!el) return
    el.volume = store.volume / 100
    el.muted = store.muted
    el.playbackRate = store.playbackRate
  }

  const applyConfigFromAdapter = (): void => {
    const hasVolume = config.value.volume !== undefined
    const hasMuted = config.value.muted !== undefined
    const hasPlaybackRate = config.value.playbackRate !== undefined

    if (!hasVolume && !hasMuted && !hasPlaybackRate) return

    if (hasVolume) store.setVolume(config.value.volume as number)
    if (hasMuted) store.setMuted(config.value.muted as boolean)
    if (hasPlaybackRate) store.setPlaybackRate(config.value.playbackRate as number)
  }



  const setQuality = (quality: string | number): void => {
    const qualityLabel = String(quality)
    if (typeof quality === 'number') {
      currentQualityId.value = quality
      registeredQualityId.value = quality
    }
    currentQualityLabel.value = qualityLabel
    store.setCurrentQuality(qualityLabel, registeredQualityId.value ?? null)

    // 通知插件
    const hlsPlugin = pluginManager.get<HlsPlugin>('hls')
    const dashPlugin = pluginManager.get<DashPlugin>('dash')
    
    if (hlsPlugin && isHlsStream.value) {
      hlsPlugin.setQuality(quality)
    } else if (dashPlugin && isDashStream.value) {
      dashPlugin.setQuality(quality)
    } else if (dashPlugin) {
      dashPlugin.setQuality(quality)
    } else if (hlsPlugin) {
      hlsPlugin.setQuality(quality)
    }
    
    events.emit('qualitychange', { quality: qualityLabel, auto: qualityLabel === 'auto' })
    onQualityChange?.(qualityLabel)
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
        store.setPictureInPicture(false)
      } else {
        await videoElement.value.requestPictureInPicture()
        store.setPictureInPicture(true)
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

  // ===== 源类型检测 =====
  const detectSourceType = (src: string): 'hls' | 'dash' | 'native' => {
    const url = src.toLowerCase()
    
    // HLS 检测
    if (url.includes('.m3u8') || url.includes('format=m3u8')) {
      return 'hls'
    }
    
    // DASH 检测: .mpd, /mpd, format=mpd
    if (url.includes('.mpd') || url.includes('/mpd') || url.includes('format=mpd')) {
      return 'dash'
    }
    
    return 'native'
  }

  // ===== 源加载 =====
  let pendingSource: MediaSource | null = null
  let autoPlayOnReady = false
  let currentSourceUrl = ''

  const loadSource = (source: MediaSource): void => {
    if (!source.src) {
      console.warn('[usePlayer] No source URL provided')
      return
    }

    // 立即重置播放器状态（无论是否能立即加载）
    store.setCurrentTime(0)
    store.setDuration(0)
    store.setBufferedProgress(0)
    store.setPlaying(false)
    store.setLoading(true, 'fetching')
    currentQualityLabel.value = null
    store.setCurrentQuality(null, null)
    currentQualityId.value = null
    registeredQualityId.value = null


    // 解析源类型
    const resolvedSource: MediaSource = {
      ...source,
      type: source.type === 'auto' || !source.type 
        ? detectSourceType(source.src) 
        : source.type
    }

    // 如果插件或视频元素还没准备好，保存待处理的源
    if (!isReady.value || !videoElement.value) {
      pendingSource = resolvedSource
      return
    }

    doLoadSource(resolvedSource)
  }

  const doLoadSource = (source: MediaSource): void => {
    if (!videoElement.value) {
      pendingSource = source
      return
    }

    const { src, type = 'native' } = source

    // 避免重复加载相同的源
    if (src === currentSourceUrl) return

    // 切换源之前先暂停当前视频，避免旧视频继续播放
    if (videoElement.value) {
      try {
        videoElement.value.pause()
      } catch (e) {
        // Ignore pause errors
      }
    }

    currentSourceUrl = src

    // 通知插件源变化（HLS/DASH 插件会处理）
    events.emit('sourcechange', { src, type })
    
    // 原生视频直接设置 src
    if (type === 'native') {
      videoElement.value.src = src
      videoElement.value.load()
    }

    // 设置海报
    if (source.poster && videoElement.value) {
      videoElement.value.poster = source.poster
    }

    // 自动播放：监听 canplay 事件
    if (store.autoplay) {
      autoPlayOnReady = true
    }
  }

  // ===== 字幕管理 =====
  const setSubtitleTracks = (tracks: SubtitleTrack[]): void => {
    subtitleTracks.value = tracks
    
    const subtitlesPlugin = pluginManager.get<SubtitlesPlugin>('subtitles')
    if (subtitlesPlugin) {
      subtitlesPlugin.setTracks(tracks)
    }
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
        onBandwidthSample: (loaded: number, duration: number) => {
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

    // 加载待处理的视频源（仅在 videoElement 也准备好时）
    if (pendingSource && videoElement.value) {
      const source = pendingSource
      pendingSource = null
      doLoadSource(source)
    }
  }

  // ===== 事件监听 =====
  let listenersSetup = false
  const setupVideoListeners = (): void => {
    if (!videoElement.value) return

    // 防止重复设置
    if (listenersSetup) return
    listenersSetup = true

    const video = videoElement.value

    video.addEventListener('play', () => {
      store.setPlaying(true)
      store.setHasStartedPlayback(true)
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

    video.addEventListener('loadedmetadata', () => {
      store.setDuration(video.duration)
      events.emit('loadedmetadata', { 
        duration: video.duration, 
        videoWidth: video.videoWidth, 
        videoHeight: video.videoHeight 
      })
    })

    video.addEventListener('progress', () => {
      if (video.buffered.length > 0 && video.duration > 0) {
        const bufferedEnd = video.buffered.end(video.buffered.length - 1)
        const percent = (bufferedEnd / video.duration) * 100
        store.setBufferedProgress(percent)
        events.emit('progress', { buffered: video.buffered, duration: video.duration })
      }
    })

    video.addEventListener('volumechange', () => {
      const volumeValue = video.volume * 100
      store.setVolume(volumeValue)
      store.setMuted(video.muted)
      adapterSaveConfig({ volume: volumeValue, muted: video.muted })
      events.emit('volumechange', { volume: volumeValue / 100, muted: video.muted })
    })


    video.addEventListener('waiting', () => {
      store.setLoading(true, 'buffering')
      events.emit('waiting', undefined)
    })

    video.addEventListener('canplay', () => {
      store.setLoading(false, 'ready')
      store.setCanPlay('video', true)
      events.emit('canplay', undefined)
      
      // 自动播放
      if (autoPlayOnReady) {
        autoPlayOnReady = false
        play().catch(() => {
          // 自动播放被浏览器阻止，静默处理
        })
      }
    })

    video.addEventListener('error', (e) => {
      const error: PlayerError = {
        code: 'MEDIA_ERROR',
        message: 'Video playback error',
        fatal: true,
        details: e
      }
      void handleRecoveryError(error)
        .then((recovered) => {
          if (!recovered) {
            reportFatalError(error)
          }
        })
        .catch(() => {
          reportFatalError(error)
        })
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

    await adapterLoadConfig()
    applyConfigFromAdapter()

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
  watch(videoElement, async (el) => {
    if (el) {
      setupVideoListeners()
      syncMediaElementSettings(el)
      
      // 如果插件已准备好但有待处理的源，现在加载它
      if (isReady.value && pendingSource) {
        doLoadSource(pendingSource)
        pendingSource = null
      }
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
    currentQualityLabel,
    currentQualityId,
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
    setSubtitleTracks,
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

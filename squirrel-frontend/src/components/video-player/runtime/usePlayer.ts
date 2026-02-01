import { computed, onMounted, onUnmounted, ref, watch, type ComputedRef, type Ref } from 'vue'

import { useI18n, type LocaleCode, type LocaleMessages, type UseI18nOptions } from '../i18n'
import { useTheme, type ThemeName, type UseThemeOptions } from '../themes'

import { createPlayerRuntimeStore, type PlayerRuntimeStore } from './PlayerStore'
import { createPlayerEngine, type PlayerEngine, type PlayerEngineOptions } from '../core/createPlayerEngine'
import { createDefaultPlayerPlugins } from '../core/defaultPlugins'
import { useA11y } from './useA11y'
import { useControlsLayout } from './useControlsLayout'
import { useGestures } from './useGestures'
import { useIcons } from '../core/useIcons'
import type { UserConfig } from '../core/PlayerAdapter'
import type { MediaSource, PlayerError, PluginConfig, QualityLevel, SubtitleTrack } from '../core/types'

export interface PlayerOptions {
  autoplay?: boolean
  autoplayNext?: boolean
  muted?: boolean
  volume?: number
  loop?: boolean

  theme?: ThemeName
  themeOptions?: Omit<UseThemeOptions, 'defaultTheme' | 'target'>
  locale?: LocaleCode
  i18nOptions?: Omit<UseI18nOptions, 'locale' | 'logger'>

  enableHls?: boolean
  enableDash?: boolean
  enableSubtitles?: boolean
  enableAnalytics?: boolean
  enableGestures?: boolean

  adapter?: PlayerEngineOptions['adapter']
  plugins?: PluginConfig[]
  useDefaultPlugins?: boolean

  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onError?: (error: PlayerError) => void
  onTimeUpdate?: (time: number) => void
  onQualityChange?: (quality: string) => void
}

export interface PlayerReturn {
  store: PlayerRuntimeStore

  videoElement: Ref<HTMLVideoElement | null>
  containerElement: Ref<HTMLElement | null>

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

  isHlsStream: ComputedRef<boolean>
  isDashStream: ComputedRef<boolean>

  play: () => Promise<void>
  pause: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  toggleMute: () => void
  setPlaybackRate: (rate: number) => void
  setQuality: (quality: string | number) => void
  setAutoplayNext: (autoplayNext: boolean) => void
  setLoop: (loop: boolean) => void
  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>

  subtitleTracks: Ref<SubtitleTrack[]>
  currentSubtitle: Ref<SubtitleTrack | null>
  setSubtitle: (track: SubtitleTrack | null) => void
  setSubtitleTracks: (tracks: SubtitleTrack[]) => void
  toggleSubtitles: () => void

  loadSource: (source: MediaSource) => void

  theme: Ref<ThemeName>
  setTheme: (theme: ThemeName) => void

  t: (key: keyof LocaleMessages, params?: Record<string, string | number>) => string
  locale: Ref<LocaleCode>
  setLocale: (locale: LocaleCode) => void

  saveProgress: () => void
  loadProgress: (progressKey: string) => Promise<number | null>

  announce: (message: string) => void

  getPlugin: <T>(name: string) => T | null
  on: PlayerEngine['on']
  off: PlayerEngine['off']

  controlsLayout: ReturnType<typeof useControlsLayout>
  icons: ReturnType<typeof useIcons>

  destroy: () => void
}

export function usePlayer(options: PlayerOptions = {}): PlayerReturn {
  const {
    autoplay = false,
    autoplayNext = true,
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
    adapter,
    plugins,
    useDefaultPlugins = true,
    onPlay,
    onPause,
    onEnded,
    onError,
    onTimeUpdate,
    onQualityChange,
  } = options

  const store = createPlayerRuntimeStore()
  const videoElement = ref<HTMLVideoElement | null>(null)
  const containerElement = ref<HTMLElement | null>(null)
  const isReady = ref(false)

  const qualities = ref<QualityLevel[]>([])
  const currentQualityLabel = ref<string | null>(null)
  const currentQualityId = ref<number | null>(null)

  const subtitleTracks = ref<SubtitleTrack[]>([])
  const currentSubtitle = ref<SubtitleTrack | null>(null)

  const sourceType = ref<'native' | 'hls' | 'dash' | null>(null)

  const isPlaying = computed(() => store.playing)
  const isPaused = computed(() => !store.playing)
  const currentTime = computed(() => store.currentTime)
  const duration = computed(() => store.duration)
  const volumeValue = computed(() => store.volume)
  const isMuted = computed(() => store.muted)
  const isFullscreen = computed(() => store.fullscreen)

  const isHlsStream = computed(() => sourceType.value === 'hls')
  const isDashStream = computed(() => sourceType.value === 'dash')

  const controlsLayout = useControlsLayout({ layout: 'default' })
  const icons = useIcons()

  const { theme, setTheme: applyTheme } = useTheme({ ...(options.themeOptions ?? {}), defaultTheme: initialTheme, target: containerElement })
  const setTheme = (newTheme: ThemeName) => applyTheme(newTheme)

  const { t, locale, setLocale } = useI18n({ ...(options.i18nOptions ?? {}), locale: initialLocale as any })

  const { announce } = useA11y({ videoElement, containerElement, t })

  const enginePlugins = plugins ?? (
    useDefaultPlugins
      ? createDefaultPlayerPlugins({ enableHls, enableDash, enableSubtitles, enableAnalytics })
      : []
  )

  const engine = createPlayerEngine({
    autoplay,
    autoplayNext,
    muted,
    volume,
    loop,
    adapter,
    plugins: enginePlugins,
    onPlay,
    onPause,
    onEnded,
    onError,
    onTimeUpdate,
    onQualityChange,
  })

  const updateStoreFromConfig = (cfg: UserConfig) => {
    if (cfg.autoplay !== undefined) store.setAutoplay(!!cfg.autoplay)
    if (cfg.autoplayNext !== undefined) store.setAutoplayNext(!!cfg.autoplayNext)
    if (cfg.loop !== undefined) store.setLoop(!!cfg.loop)
    if (cfg.volume !== undefined) store.setVolume(cfg.volume as number)
    if (cfg.muted !== undefined) store.setMuted(cfg.muted as boolean)
    if (cfg.playbackRate !== undefined) store.setPlaybackRate(cfg.playbackRate as number)
  }

  engine.on('play', () => {
    store.setPlaying(true)
    store.setHasStartedPlayback(true)
  })

  engine.on('pause', () => {
    store.setPlaying(false)
  })

  engine.on('timeupdate', ({ currentTime, duration }) => {
    store.setCurrentTime(currentTime)
    if (isFinite(duration) && !isNaN(duration)) store.setDuration(duration)
  })

  engine.on('durationchange', (d) => {
    if (!isFinite(d) || isNaN(d)) return
    store.setDuration(d)
  })

  engine.on('loadedmetadata', ({ duration }) => {
    if (!isFinite(duration) || isNaN(duration)) return
    store.setDuration(duration)
  })

  engine.on('progress', ({ buffered, duration }) => {
    if (!isFinite(duration) || isNaN(duration) || duration <= 0) return
    if (buffered.length <= 0) return
    const bufferedEnd = buffered.end(buffered.length - 1)
    store.setBufferedProgress((bufferedEnd / duration) * 100)
  })

  engine.on('volumechange', ({ volume, muted }) => {
    store.setVolume(volume * 100)
    store.setMuted(muted)
  })

  engine.on('waiting', () => {
    store.setLoading(true, 'buffering')
  })

  engine.on('canplay', () => {
    store.setLoading(false, 'ready')
    store.setCanPlay('video', true)
  })

  engine.on('fullscreenchange', (isFs) => {
    store.setFullscreen(isFs)
  })

  engine.on('sourcetypechange', (type) => {
    sourceType.value = type
  })

  engine.on('qualitiesloaded', (qs) => {
    qualities.value = qs
  })

  engine.on('qualitychange', ({ quality, id }) => {
    currentQualityLabel.value = quality
    store.setCurrentQuality(quality, typeof id === 'number' ? id : null)
    currentQualityId.value = typeof id === 'number' ? id : null
  })

  engine.on('error', () => {
    store.setLoading(false, 'idle')
    store.setPlaying(false)
  })

  watch(videoElement, (el) => {
    engine.attachVideoElement(el)
  }, { immediate: true })

  watch(containerElement, (el) => {
    engine.attachContainerElement(el)
  }, { immediate: true })

  const play = async (): Promise<void> => {
    await engine.play()
  }

  const pause = (): void => {
    engine.pause()
  }

  const seek = (time: number): void => {
    engine.seek(time)
  }

  const setVolume = (value: number): void => {
    engine.setVolume(value)
  }

  const toggleMute = (): void => {
    engine.toggleMute()
  }

  const setPlaybackRate = (rate: number): void => {
    store.setPlaybackRate(rate)
    engine.setPlaybackRate(rate)
  }

  const setAutoplayNext = (value: boolean): void => {
    store.setAutoplayNext(value)
    engine.setAutoplayNext(value)
  }

  const setLoop = (value: boolean): void => {
    store.setLoop(value)
    engine.setLoop(value)
  }

  const setQuality = (quality: string | number): void => {
    engine.setQuality(quality)
  }

  const toggleFullscreen = async (): Promise<void> => {
    await engine.toggleFullscreen()
  }

  const togglePictureInPicture = async (): Promise<void> => {
    await engine.togglePictureInPicture()
  }

  const setSubtitle = (track: SubtitleTrack | null): void => {
    currentSubtitle.value = track
    store.setCurrentSubtitle(track)
    store.setSubtitlesEnabled(!!track)
    engine.setSubtitle(track)
  }

  const setSubtitleTracks = (tracks: SubtitleTrack[]): void => {
    subtitleTracks.value = tracks
    engine.setSubtitleTracks(tracks)
  }

  const toggleSubtitles = (): void => {
    engine.toggleSubtitles()
    const subtitlesPlugin = engine.getPlugin<any>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.isEnabled === 'function') {
      store.setSubtitlesEnabled(!!subtitlesPlugin.isEnabled())
    }
  }

  const loadSource = (source: MediaSource): void => {
    store.setCurrentTime(0)
    store.setDuration(0)
    store.setBufferedProgress(0)
    store.setPlaying(false)
    store.setLoading(true, 'fetching')
    currentQualityLabel.value = null
    currentQualityId.value = null
    store.setCurrentQuality(null, null)
    engine.loadSource(source)
  }

  const saveProgress = (): void => {
    engine.saveProgress()
  }

  const loadProgress = async (key: string): Promise<number | null> => {
    return await engine.loadProgress(key)
  }

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
          if (store.playing) pause()
          else void play()
        }
      }
    })
  }

  onMounted(async () => {
    store.setAutoplay(autoplay)
    store.setAutoplayNext(autoplayNext)
    store.setMuted(muted)
    store.setVolume(volume)
    store.setLoop(loop)

    await engine.init()

    updateStoreFromConfig(engine.getConfig())
    isReady.value = true
  })

  const destroy = (): void => {
    engine.destroy()
  }

  onUnmounted(() => {
    destroy()
  })

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
    setAutoplayNext,
    setLoop,
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
    getPlugin: engine.getPlugin,
    on: engine.on,
    off: engine.off,
    controlsLayout,
    icons,
    destroy,
  }
}

export default usePlayer

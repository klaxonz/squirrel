import { computed, onMounted, onUnmounted, ref, watch, type ComputedRef, type Ref } from 'vue'

import { useI18n, type LocaleCode, type LocaleMessages, type UseI18nOptions } from '../i18n'
import { useTheme, type ThemeName, type UseThemeOptions } from '../themes'

import { createPlayerRuntimeStore, type PlayerRuntimeStore } from './PlayerStore'
import { createPlayerEngine, type PlayerEngine, type PlayerEngineOptions } from '../core/createPlayerEngine'
import { createDefaultPlayerPlugins } from '../core/defaultPlugins'
import { BUILT_IN_PRESETS } from '../plugins/subtitles'
import { useA11y } from './useA11y'
import { useControlsLayout } from './useControlsLayout'

import { useIcons } from '../core/useIcons'
import { DEFAULT_SHORTCUTS, type KeyboardShortcutsConfig } from './keyboardShortcuts'
import type { UserConfig } from '../core/PlayerAdapter'
import type { MediaSource, PlayerError, PlayerStats, PluginConfig, QualityLevel, SubtitleTrack } from '../core/types'

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

  enableQualityFallback?: boolean
  keyboardShortcuts?: KeyboardShortcutsConfig

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
  codecFamilies: Ref<string[]>
  selectedCodecFamily: Ref<string>
  currentCodecFamily: Ref<string | null>
  currentQualityLabel: Ref<string | null>
  currentQualityId: Ref<string | number | null>

  isHlsStream: ComputedRef<boolean>
  isDashStream: ComputedRef<boolean>

  play: () => Promise<boolean>
  pause: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  toggleMute: () => void
  setPlaybackRate: (rate: number) => void
  setQuality: (quality: string | number) => void
  setCodecFamily: (codecFamily: string) => void
  setAutoplayNext: (autoplayNext: boolean) => void
  setLoop: (loop: boolean) => void
  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>

  subtitleTracks: Ref<SubtitleTrack[]>
  currentSubtitle: Ref<SubtitleTrack | null>
  subtitleStyle: Ref<Record<string, any>>
  subtitlePresets: typeof import('../plugins/subtitles').BUILT_IN_PRESETS
  subtitleOffset: Ref<number>
  setSubtitle: (track: SubtitleTrack | null) => void
  setSubtitleTracks: (tracks: SubtitleTrack[]) => Promise<void>
  setSubtitleStyle: (style: Record<string, any>) => void
  applySubtitlePreset: (presetId: string) => void
  toggleSubtitles: () => void
  setSubtitleOffset: (offsetSeconds: number) => void

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
  getStats: () => PlayerStats
  on: PlayerEngine['on']
  off: PlayerEngine['off']

  controlsLayout: ReturnType<typeof useControlsLayout>
  icons: ReturnType<typeof useIcons>
  keyboardShortcuts: Required<KeyboardShortcutsConfig>

  destroy: () => void
}

const calculateBufferedAheadPercent = (buffered: TimeRanges, duration: number, currentTime: number): number => {
  if (!isFinite(duration) || isNaN(duration) || duration <= 0 || buffered.length <= 0) {
    return 0
  }

  for (let index = 0; index < buffered.length; index += 1) {
    const start = buffered.start(index)
    const end = buffered.end(index)

    if (buffered.start(index) <= currentTime && currentTime <= buffered.end(index)) {
      return (end / duration) * 100
    }

    if (currentTime < start) {
      break
    }
  }

  return Math.min(100, Math.max(0, (currentTime / duration) * 100))
}

const SUBTITLE_STYLE_KEY = 'squirrel-player-subtitle-style'

const loadSubtitleStyleFromStorage = (): Record<string, any> => {
  try {
    const raw = localStorage.getItem(SUBTITLE_STYLE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

const saveSubtitleStyleToStorage = (style: Record<string, any>): void => {
  try {
    localStorage.setItem(SUBTITLE_STYLE_KEY, JSON.stringify(style))
  } catch (err) { console.warn('[SPPlayer] Failed to save subtitle style', err) }
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

    enableQualityFallback = true,
    keyboardShortcuts,
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
  const codecFamilies = ref<string[]>([])
  const selectedCodecFamily = ref<string>('auto')
  const currentCodecFamily = ref<string | null>(null)
  const currentQualityLabel = ref<string | null>(null)
  const currentQualityId = ref<string | number | null>(null)

  const subtitleTracks = ref<SubtitleTrack[]>([])
  const currentSubtitle = ref<SubtitleTrack | null>(null)
  const subtitleStyle = ref<Record<string, any>>(loadSubtitleStyleFromStorage())
  const subtitlePresets = BUILT_IN_PRESETS
  const subtitleOffset = ref(0)
  const preferredSubtitleEnabled = ref(true)
  const preferredSubtitleTrackId = ref<string | null>(null)
  const preferredSubtitleLanguage = ref<string | null>(null)
  const subtitlePreferenceReady = ref(false)

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

  const mergedShortcuts: Required<KeyboardShortcutsConfig> = {
    ...DEFAULT_SHORTCUTS,
    ...(keyboardShortcuts ?? {}),
  }

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
    errorRecovery: {
      enableQualityFallback,
    },
  })

  const syncCodecFamilies = (): void => {
    const dashPlugin = engine.getPlugin<any>('shaka-dash') || engine.getPlugin<any>('dash')
    if (!dashPlugin) {
      codecFamilies.value = []
      selectedCodecFamily.value = 'auto'
      currentCodecFamily.value = null
      return
    }

    codecFamilies.value = typeof dashPlugin.getAvailableCodecFamilies === 'function'
      ? dashPlugin.getAvailableCodecFamilies()
      : []
    selectedCodecFamily.value = typeof dashPlugin.getSelectedCodecFamily === 'function'
      ? dashPlugin.getSelectedCodecFamily()
      : 'auto'
    currentCodecFamily.value = typeof dashPlugin.getCurrentCodecFamily === 'function'
      ? dashPlugin.getCurrentCodecFamily()
      : null
  }

  const updateStoreFromConfig = (cfg: UserConfig) => {
    if (cfg.autoplay !== undefined) store.setAutoplay(!!cfg.autoplay)
    if (cfg.autoplayNext !== undefined) store.setAutoplayNext(!!cfg.autoplayNext)
    if (cfg.loop !== undefined) store.setLoop(!!cfg.loop)
    if (cfg.volume !== undefined) store.setVolume(cfg.volume as number)
    if (cfg.muted !== undefined) store.setMuted(cfg.muted as boolean)
    if (cfg.playbackRate !== undefined) store.setPlaybackRate(cfg.playbackRate as number)
    if (cfg.subtitleEnabled !== undefined) preferredSubtitleEnabled.value = !!cfg.subtitleEnabled
    if (typeof cfg.subtitleTrackId === 'string') preferredSubtitleTrackId.value = cfg.subtitleTrackId
    if (typeof cfg.subtitleLanguage === 'string') preferredSubtitleLanguage.value = cfg.subtitleLanguage
    if (cfg.subtitleEnabled === false) {
      store.setSubtitlesEnabled(false)
      store.setCurrentSubtitle(null)
      currentSubtitle.value = null
    }
  }

  const isKnownLanguage = (language: unknown): language is string => (
    typeof language === 'string'
    && language.trim().length > 0
    && language.toLowerCase() !== 'unknown'
  )

  const findPreferredSubtitleTrack = (tracks: SubtitleTrack[]): SubtitleTrack | null => {
    if (tracks.length === 0) return null

    const language = isKnownLanguage(preferredSubtitleLanguage.value)
      ? preferredSubtitleLanguage.value
      : (isKnownLanguage(currentSubtitle.value?.language) ? currentSubtitle.value.language : null)

    if (language) {
      const languageMatch = tracks.find((track) => track.language === language)
      if (languageMatch) return languageMatch
    }

    const trackId = preferredSubtitleTrackId.value || currentSubtitle.value?.id
    if (trackId) {
      const idMatch = tracks.find((track) => track.id === trackId)
      if (idMatch) return idMatch
    }

    return tracks.find((track) => track.default) || tracks[0] || null
  }

  const markPlaybackActive = () => {
    store.setPlaying(true)
    store.setHasStartedPlayback(true)
    store.setLoading(false, 'ready')
    store.setCanPlay('video', true)
  }

  engine.on('play', () => {
    markPlaybackActive()
  })

  engine.on('playing', () => {
    markPlaybackActive()
  })

  engine.on('pause', () => {
    store.setPlaying(false)
  })

  engine.on('timeupdate', ({ currentTime, duration }) => {
    store.setCurrentTime(currentTime)
    if (isFinite(duration) && !isNaN(duration)) store.setDuration(duration)
  })

  engine.on('seeking', (time) => {
    if (!isFinite(time) || isNaN(time)) return
    const duration = store.duration
    const nextTime = Math.max(0, time)
    store.setCurrentTime((isFinite(duration) && !isNaN(duration) && duration > 0) ? Math.min(nextTime, duration) : nextTime)
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
    store.setBufferedProgress(calculateBufferedAheadPercent(buffered, duration, store.currentTime))
  })

  engine.on('loadsstart', () => {
    store.setCanPlay('video', false)
    store.setLoading(true, 'fetching')
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

  engine.on('enterpictureinpicture', () => {
    store.setPictureInPicture(true)
  })

  engine.on('leavepictureinpicture', () => {
    store.setPictureInPicture(false)
  })

  engine.on('sourcetypechange', (type) => {
    sourceType.value = type
    if (type !== 'dash') {
      codecFamilies.value = []
      selectedCodecFamily.value = 'auto'
      currentCodecFamily.value = null
      return
    }
    syncCodecFamilies()
  })

  engine.on('qualitiesloaded', (qs) => {
    qualities.value = qs
    syncCodecFamilies()
  })

  engine.on('qualitychange', ({ quality, id }) => {
    currentQualityLabel.value = quality
    store.setCurrentQuality(quality, id ?? null)
    currentQualityId.value = id ?? null
    syncCodecFamilies()
  })

  engine.on('error', () => {
    store.setLoading(false, 'idle')
    store.setPlaying(false)
  })

  engine.on('ended', () => {
    store.setLoading(false, 'idle')
  })

  watch(videoElement, (el) => {
    engine.attachVideoElement(el)
  }, { immediate: true })

  watch(containerElement, (el) => {
    engine.attachContainerElement(el)
  }, { immediate: true })

  const play = async (): Promise<boolean> => {
    return await engine.play()
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

  const setCodecFamily = (codecFamily: string): void => {
    const dashPlugin = engine.getPlugin<any>('shaka-dash') || engine.getPlugin<any>('dash')
    if (dashPlugin && typeof dashPlugin.setCodecFamily === 'function') {
      dashPlugin.setCodecFamily(codecFamily)
      syncCodecFamilies()
    }
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
    preferredSubtitleEnabled.value = !!track
    preferredSubtitleTrackId.value = track?.id || null
    preferredSubtitleLanguage.value = isKnownLanguage(track?.language) ? track.language : null
    engine.setSubtitle(track)
  }

  const setSubtitleStyle = (style: Record<string, any>): void => {
    subtitleStyle.value = { ...subtitleStyle.value, ...style }
    engine.setSubtitleStyle(subtitleStyle.value)
    saveSubtitleStyleToStorage(subtitleStyle.value)
  }

  const applySubtitlePreset = (presetId: string): void => {
    engine.applySubtitlePreset(presetId)
    subtitleStyle.value = engine.getSubtitleStyle()
    saveSubtitleStyleToStorage(subtitleStyle.value)
  }

  const setSubtitleOffset = (offsetSeconds: number): void => {
    subtitleOffset.value = offsetSeconds
    engine.setSubtitleOffset(offsetSeconds)
  }

  const setSubtitleTracks = async (tracks: SubtitleTrack[]): Promise<void> => {
    subtitleTracks.value = tracks
    if (!subtitlePreferenceReady.value) return

    await engine.setSubtitleTracks(tracks)

    if (tracks.length === 0) {
      currentSubtitle.value = null
      store.setCurrentSubtitle(null)
      store.setSubtitlesEnabled(false)
      return
    }

    if (preferredSubtitleEnabled.value) {
      const nextTrack = findPreferredSubtitleTrack(tracks)
      setSubtitle(nextTrack)
      return
    }

    currentSubtitle.value = null
    store.setCurrentSubtitle(null)
    store.setSubtitlesEnabled(false)
    engine.setSubtitle(null)
  }

  const toggleSubtitles = (): void => {
    if (store.subtitlesEnabled) {
      setSubtitle(null)
      return
    }

    setSubtitle(findPreferredSubtitleTrack(subtitleTracks.value))
  }

  const loadSource = (source: MediaSource): void => {
    store.setCurrentTime(0)
    store.setDuration(0)
    store.setBufferedProgress(0)
    store.setPlaying(false)
    store.setLoading(true, 'fetching')
    currentQualityLabel.value = null
    currentQualityId.value = null
    codecFamilies.value = []
    selectedCodecFamily.value = 'auto'
    currentCodecFamily.value = null
    store.setCurrentQuality(null, null)
    engine.loadSource(source)
  }

  const saveProgress = (): void => {
    engine.saveProgress()
  }

  const loadProgress = async (key: string): Promise<number | null> => {
    return await engine.loadProgress(key)
  }

  onMounted(async () => {
    store.setAutoplay(autoplay)
    store.setAutoplayNext(autoplayNext)
    store.setMuted(muted)
    store.setVolume(volume)
    store.setLoop(loop)

    await engine.init()
    updateStoreFromConfig(engine.getConfig())
    subtitlePreferenceReady.value = true

    if (Object.keys(subtitleStyle.value).length > 0) {
      engine.setSubtitleStyle(subtitleStyle.value)
    }
    if (subtitleTracks.value.length > 0) {
      await setSubtitleTracks(subtitleTracks.value)
    }

    syncCodecFamilies()
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
    codecFamilies,
    selectedCodecFamily,
    currentCodecFamily,
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
    setCodecFamily,
    setAutoplayNext,
    setLoop,
    toggleFullscreen,
    togglePictureInPicture,
    subtitleTracks,
    currentSubtitle,
    subtitleStyle,
    subtitlePresets,
    subtitleOffset,
    setSubtitle,
    setSubtitleTracks,
    setSubtitleStyle,
    applySubtitlePreset,
    toggleSubtitles,
    setSubtitleOffset,
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
    getStats: () => engine.getStats(),
    on: engine.on,
    off: engine.off,
    controlsLayout,
    icons,
    keyboardShortcuts: mergedShortcuts,
    destroy,
  }
}

export default usePlayer

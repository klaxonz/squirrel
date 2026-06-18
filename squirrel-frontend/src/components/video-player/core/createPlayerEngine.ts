import { EventEmitter } from './EventEmitter'
import { PluginManager } from './PluginManager'
import { MemoryAdapter, type IPlayerAdapter, type UserConfig, type PlaybackProgress } from './PlayerAdapter'
import { playerLogger } from './logger'
import { createErrorRecovery, MAX_VOLUME, detectSourceType } from './error-recovery'
import type {
  MediaSource,
  PlayerError,
  PlayerEvents,
  PlayerState,
  PlayerStats,
  QualityLevel,
  QualitySelectionRequest,
  PluginConfig,
  PluginContext,
  SubtitleTrack,
} from './types'

// ponytail: structural views of player plugins the engine drives. Typed
// structurally (only the methods the engine actually calls) to avoid importing
// the concrete plugin classes, which would create a runtime cycle
// (plugins -> core).
interface QualityController {
  setQuality?: (quality: unknown) => void
}
interface SubtitleController {
  setTracks?: (tracks: SubtitleTrack[]) => Promise<void>
  loadTrack?: (track: SubtitleTrack) => boolean | Promise<boolean | void>
  enable?: () => void
  disable?: () => void
  toggle?: () => void
  exportStyle?: () => Record<string, unknown>
  importStyle?: (style: Record<string, unknown>) => void
  applyPreset?: (presetId: string) => void
  setSubtitleOffset?: (offsetSeconds: number) => void
  getSubtitleOffset?: () => number
}

export type PlayerEngineOptions = {
  autoplay?: boolean
  autoplayNext?: boolean
  muted?: boolean
  volume?: number
  loop?: boolean
  playbackRate?: number

  adapter?: IPlayerAdapter
  plugins?: PluginConfig[]

  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onError?: (error: PlayerError) => void
  onTimeUpdate?: (time: number) => void
  onQualityChange?: (quality: string) => void

  errorRecovery?: {
    maxRetries?: number
    retryDelay?: number
    enableQualityFallback?: boolean
  }

  progress?: {
    saveInterval?: number
    thresholdSeconds?: number
  }
}

export type PlayerEngine = {
  attachVideoElement: (el: HTMLVideoElement | null) => void
  attachContainerElement: (el: HTMLElement | null) => void

  init: () => Promise<void>
  destroy: () => void

  play: () => Promise<boolean>
  pause: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  setMuted: (muted: boolean) => void
  toggleMute: () => void
  setPlaybackRate: (rate: number) => void
  setLoop: (loop: boolean) => void
  setAutoplay: (autoplay: boolean) => void
  setAutoplayNext: (autoplayNext: boolean) => void

  setQuality: (quality: QualitySelectionRequest) => void

  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>

  loadSource: (source: MediaSource) => void
  getSource: () => MediaSource | null
  getSourceType: () => 'native' | 'hls' | 'dash' | null

  setSubtitleTracks: (tracks: SubtitleTrack[]) => Promise<void>
  setSubtitle: (track: SubtitleTrack | null) => void
  toggleSubtitles: () => void
  getSubtitleStyle: () => Record<string, unknown>
  setSubtitleStyle: (style: Record<string, unknown>) => void
  applySubtitlePreset: (presetId: string) => void
  setSubtitleOffset: (offsetSeconds: number) => void
  getSubtitleOffset: () => number

  saveProgress: () => void
  loadProgress: (progressKey: string) => Promise<number | null>

  getConfig: () => UserConfig
  getQualities: () => QualityLevel[]
  getCurrentQualityLabel: () => string | null
  getCurrentQualityId: () => string | number | null
  getSubtitleTracks: () => SubtitleTrack[]
  getCurrentSubtitle: () => SubtitleTrack | null

  getPlugin: <T>(name: string) => T | null
  getStats: () => PlayerStats
  on: EventEmitter<PlayerEvents>['on']
  off: EventEmitter<PlayerEvents>['off']
}

export function createPlayerEngine(options: PlayerEngineOptions = {}): PlayerEngine {
  const logger = playerLogger
  const adapter = options.adapter ?? new MemoryAdapter()

  const events = new EventEmitter<PlayerEvents>()
  const pluginManager = new PluginManager(events)

  let videoElement: HTMLVideoElement | null = null
  let containerElement: HTMLElement | null = null
  let audioContext: AudioContext | null = null
  let audioSourceNode: MediaElementAudioSourceNode | null = null
  let audioGainNode: GainNode | null = null
  let audioGainElement: HTMLVideoElement | null = null

  let inited = false
  let destroyed = false

  let config: UserConfig = {}

  let autoplay = !!options.autoplay
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- read via getAutoplayNext; flagged due to control-flow write shape
  let autoplayNext = options.autoplayNext !== false
  let muted = !!options.muted
  let volume = typeof options.volume === 'number' ? Math.max(0, Math.min(MAX_VOLUME, options.volume)) : 100
  let loop = !!options.loop
  let playbackRate = typeof options.playbackRate === 'number' ? options.playbackRate : 1

  let loading = false
  let bufferedProgress = 0

  let qualities: QualityLevel[] = []
  let currentQualityLabel: string | null = null
  let currentQualityId: string | number | null = null
  let registeredQualityId: string | number | null = null

  let subtitleTracks: SubtitleTrack[] = []
  let currentSubtitle: SubtitleTrack | null = null
  let subtitleLoadRequestId = 0

  let progressKey: string | null = null

  let currentSource: MediaSource | null = null
  let currentSourceType: 'native' | 'hls' | 'dash' | null = null
  let currentSourceKey = ''
  let pendingSource: MediaSource | null = null
  let pendingSourceKey = ''
  let autoPlayOnReady = false
  let mediaLoadStartedForCurrentSource = false
  let mediaMetadataLoadedForCurrentSource = false

  let lastSavedTime = 0
  let lastSavedAt = 0
  let pendingProgress: PlaybackProgress | null = null
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  const progressSaveInterval = options.progress?.saveInterval ?? 2000
  const progressThreshold = options.progress?.thresholdSeconds ?? 5

  const maxRetries = options.errorRecovery?.maxRetries ?? 3
  const retryDelay = options.errorRecovery?.retryDelay ?? 2000
  const enableQualityFallback = options.errorRecovery?.enableQualityFallback ?? false

  let pluginHandlingError = false
  let retryCount = 0

  const releaseVideoElementMedia = (video: HTMLVideoElement | null): void => {
    if (!video) return

    try {
      video.pause()
    } catch (e) {
      logger.warn('[PlayerEngine] Failed to pause video during release', e)
    }

    video.removeAttribute('src')
    video.removeAttribute('poster')

    try {
      video.load()
    } catch (e) {
      logger.warn('[PlayerEngine] Failed to load video during release', e)
    }
  }

  const resetProgressState = (): void => {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    pendingProgress = null
    lastSavedTime = 0
    lastSavedAt = 0
  }

  const setProgressKey = (key: string | null): void => {
    if (progressKey !== key) {
      resetProgressState()
    }
    progressKey = key
  }

  const getState = (): PlayerState => {
    const video = videoElement
    return {
      playing: video ? !video.paused : false,
      paused: video?.paused ?? true,
      ended: video?.ended ?? false,
      waiting: loading,
      seeking: video?.seeking ?? false,
      currentTime: video?.currentTime ?? 0,
      duration: video?.duration ?? 0,
      buffered: bufferedProgress,
      volume: volume / 100,
      muted: video?.muted ?? muted,
      playbackRate: video?.playbackRate ?? playbackRate,
      fullscreen: typeof document !== 'undefined' ? !!document.fullscreenElement : false,
      pip: typeof document !== 'undefined' ? document.pictureInPictureElement === video : false,
      quality: currentQualityLabel,
      autoQuality: currentQualityLabel === 'auto'
    }
  }

  const applyAudioGain = (el: HTMLVideoElement): void => {
    if (!audioContext) {
      audioContext = new AudioContext()
    }
    if (!audioGainNode || audioGainElement !== el) {
      audioSourceNode?.disconnect()
      audioGainNode?.disconnect()
      audioSourceNode = audioContext.createMediaElementSource(el)
      audioGainNode = audioContext.createGain()
      audioSourceNode.connect(audioGainNode)
      audioGainNode.connect(audioContext.destination)
      audioGainElement = el
    }
    el.volume = 1
    audioGainNode.gain.value = Math.max(0, Math.min(MAX_VOLUME, volume)) / 100
  }

  const applyMediaSettings = (el: HTMLVideoElement | null): void => {
    if (!el) return
    if (volume > 100 || audioGainNode) {
      applyAudioGain(el)
    } else {
      el.volume = Math.max(0, Math.min(1, volume / 100))
    }
    el.muted = muted
    el.playbackRate = playbackRate
    el.loop = loop
  }

  const saveConfigPatch = (patch: Partial<UserConfig>): void => {
    config = { ...config, ...patch }
    void adapter.saveConfig(patch)
  }

  const applyConfig = (next: UserConfig): void => {
    const hasAutoplay = next.autoplay !== undefined
    const hasAutoplayNext = next.autoplayNext !== undefined
    const hasLoop = next.loop !== undefined
    const hasVolume = next.volume !== undefined
    const hasMuted = next.muted !== undefined
    const hasPlaybackRate = next.playbackRate !== undefined

    if (!hasAutoplay && !hasAutoplayNext && !hasLoop && !hasVolume && !hasMuted && !hasPlaybackRate) return

    if (hasAutoplay) autoplay = !!next.autoplay
    if (hasAutoplayNext) autoplayNext = !!next.autoplayNext
    if (hasLoop) loop = !!next.loop
    if (hasVolume) volume = Math.max(0, Math.min(MAX_VOLUME, next.volume as number))
    if (hasMuted) muted = next.muted as boolean
    if (hasPlaybackRate) playbackRate = next.playbackRate as number

    applyMediaSettings(videoElement)
  }

  const resolveMediaUrl = (src: string): string => {
    try {
      return new URL(src, window.location.href).href
    } catch {
      logger.debug('[PlayerEngine] Failed to resolve media URL', src)
      return src
    }
  }

  const isNativeMediaSourceCurrent = (): boolean => {
    if (!videoElement || !currentSource || currentSourceType !== 'native') return true
    if (!videoElement.currentSrc) return false
    return resolveMediaUrl(videoElement.currentSrc) === resolveMediaUrl(currentSource.src)
  }

  const markSourceLoadingStarted = (): void => {
    loading = true
    mediaLoadStartedForCurrentSource = false
    mediaMetadataLoadedForCurrentSource = false
    events.emit('loadsstart', undefined)
  }

  const canAcceptNativeCanPlay = (): boolean => {
    if (!isNativeMediaSourceCurrent()) return false
    if (!loading) return true
    return mediaLoadStartedForCurrentSource && mediaMetadataLoadedForCurrentSource
  }

  const errorRecovery = createErrorRecovery({
    getVideoElement: () => videoElement,
    getLoading: () => loading,
    setLoading: (v) => { loading = v },
    getRetryCount: () => retryCount,
    setRetryCount: (v) => { retryCount = v },
    getQualities: () => qualities,
    setQualities: (qs) => { qualities = qs },
    getRegisteredQualityId: () => registeredQualityId,
    getCurrentSource: () => currentSource,
    getCurrentSourceType: () => currentSourceType,
    getCurrentSourceKey: () => currentSourceKey,
    setCurrentSourceKey: (k) => { currentSourceKey = k },
    getPendingSourceKey: () => pendingSourceKey,
    setPendingSourceKey: (k) => { pendingSourceKey = k },
    getAutoPlayOnReady: () => autoPlayOnReady,
    setAutoPlayOnReady: (v) => { autoPlayOnReady = v },
    getProgressKey: () => progressKey,
    getMaxRetries: () => maxRetries,
    getRetryDelay: () => retryDelay,
    getEnableQualityFallback: () => enableQualityFallback,
    events,
    pluginManager,
    logger,
    adapter,
    onError: options.onError,
    play: () => play(),
    setQuality: (q) => setQuality(q),
    doLoadSource: (s) => doLoadSource(s),
  })

  const createPluginContext = (): PluginContext => ({
    get videoElement() { return videoElement },
    get state() { return getState() },
    logger,

    on: events.on.bind(events),
    off: events.off.bind(events),
    emit(event, payload) {
      if (event === 'waiting') {
        loading = true
        errorRecovery.scheduleWaitingRecovery()
      }

      if (event === 'canplay') {
        loading = false
        retryCount = 0
        errorRecovery.clearWaitingRecovery()

        if (autoPlayOnReady) {
          autoPlayOnReady = false
          void play().catch((e) => {
            logger.warn('[PlayerEngine] Auto-play failed after canplay', e)
          })
        }
      }

      return events.emit(event, payload)
    },
    once: events.once.bind(events),

    async play() { return await play() },
    pause() { pause() },
    seek(time) { seek(time) },
    setVolume(v) { setVolume(v * 100) },
    setMuted(m) { setMuted(m) },
    setPlaybackRate(r) { setPlaybackRate(r) },

    setQuality(q) { setQuality(q) },
    getQualities() { return qualities },
    registerQualities(qs) {
      qualities = qs
      errorRecovery.setRecoveryQualities(qs)
      if (registeredQualityId !== null) {
        const match = qs.find((item) => item.id === registeredQualityId)
        if (match?.label) {
          currentQualityLabel = match.label
          currentQualityId = registeredQualityId
        }
      }
    },
    registerCurrentQualityId(id?: string | number) {
      registeredQualityId = typeof id === 'string' || typeof id === 'number' ? id : null
      if (registeredQualityId === null) return
      const match = qualities.find((item) => item.id === registeredQualityId)
      if (match?.label) {
        currentQualityLabel = match.label
        currentQualityId = registeredQualityId
      } else {
        currentQualityId = registeredQualityId
      }
    },

    setSource() { /* handled by loadSource */ },
    getSource() { return currentSource },

    async requestFullscreen() { await toggleFullscreen() },
    async exitFullscreen() {
      if (typeof document === 'undefined') return
      if (!document.fullscreenElement) return
      await toggleFullscreen()
    },
    async requestPictureInPicture() { await togglePictureInPicture() },
    async exitPictureInPicture() {
      if (typeof document === 'undefined') return
      if (!document.pictureInPictureElement) return
      await togglePictureInPicture()
    },

    reportError(error) {
      pluginHandlingError = true
      void errorRecovery.handleRecoveryError(error)
        .then((recovered) => {
          if (!recovered) errorRecovery.reportFatalError(error)
          pluginHandlingError = false
        })
        .catch((e) => {
          logger.warn('[PlayerEngine] Plugin recovery chain failed', e)
          errorRecovery.reportFatalError(error)
          pluginHandlingError = false
        })
    },
    getPlugin<T>(name: string) { return pluginManager.get(name) as T }
  })

  const initPlugins = async (): Promise<void> => {
    const context = createPluginContext()
    pluginManager.setContext(context)

    for (const item of options.plugins ?? []) {
      if (item.enabled === false) continue
      const plugin = typeof item.plugin === 'function' ? item.plugin() : item.plugin
      await pluginManager.register(plugin, item.options)
    }

    inited = true

    if (pendingSource && videoElement) {
      const source = pendingSource
      pendingSource = null
      doLoadSource(source)
    }
  }

  const doLoadSource = (source: MediaSource): void => {
    if (!videoElement) {
      pendingSource = source
      pendingSourceKey = source.key || source.src
      return
    }

    const { src, type = 'native' } = source
    const nextKey = source.key || src
    if (nextKey === currentSourceKey) return

    markSourceLoadingStarted()
    pluginHandlingError = false

    releaseVideoElementMedia(videoElement)

    currentSourceKey = nextKey
    currentSource = source
    currentSourceType = (type === 'hls' || type === 'dash' || type === 'native') ? type : null
    pendingSourceKey = ''

    events.emit('sourcetypechange', currentSourceType)
    events.emit('sourcechange', { ...source, src, type })

    if (type === 'native') {
      videoElement.src = src
      videoElement.load()
    }

    if (autoplay) {
      autoPlayOnReady = true
    }
  }

  const loadSource = (source: MediaSource): void => {
    if (!source.src) {
      logger.warn('[PlayerEngine] No source URL provided')
      return
    }

    const resolvedSource: MediaSource = {
      ...source,
      type: source.type === 'auto' || !source.type
        ? detectSourceType(source.src)
        : source.type
    }

    const nextProgressKey = resolvedSource.progressKey || resolvedSource.key || resolvedSource.src
    setProgressKey(nextProgressKey ? String(nextProgressKey) : null)

    const nextKey = resolvedSource.key || resolvedSource.src
    if (nextKey === currentSourceKey || nextKey === pendingSourceKey) return

    bufferedProgress = 0
    markSourceLoadingStarted()
    errorRecovery.clearWaitingRecovery()
    qualities = []
    currentQualityLabel = null
    currentQualityId = null
    registeredQualityId = null
    retryCount = 0
    events.emit('qualitiesloaded', [])

    currentSource = resolvedSource
    currentSourceType = (resolvedSource.type === 'hls' || resolvedSource.type === 'dash' || resolvedSource.type === 'native')
      ? resolvedSource.type
      : null

    events.emit('sourcetypechange', currentSourceType)

    if (!inited || !videoElement) {
      pendingSource = resolvedSource
      pendingSourceKey = nextKey
      return
    }

    doLoadSource(resolvedSource)
  }

  let removeVideoListeners: (() => void) | null = null
  const setupVideoListeners = (): void => {
    if (!videoElement) return
    if (removeVideoListeners) return

    const video = videoElement

    const onPlay = () => {
      errorRecovery.clearWaitingRecovery()
      events.emit('play', undefined)
      options.onPlay?.()
      adapter.trackEvent?.('play', { sourceType: currentSourceType, currentTime: video.currentTime })
    }
    const onPlaying = () => {
      loading = false
      retryCount = 0
      errorRecovery.clearWaitingRecovery()
      events.emit('playing', undefined)
    }
    const onPause = () => {
      errorRecovery.clearWaitingRecovery()
      flushProgress()
      events.emit('pause', undefined)
      options.onPause?.()
      adapter.trackEvent?.('pause', { sourceType: currentSourceType, currentTime: video.currentTime })
    }
    const onEnded = () => {
      errorRecovery.clearWaitingRecovery()
      flushProgress()
      events.emit('ended', undefined)
      options.onEnded?.()
    }
    const onTimeUpdate = () => {
      scheduleProgressSave()
      events.emit('timeupdate', { currentTime: video.currentTime, duration: video.duration })
      options.onTimeUpdate?.(video.currentTime)
    }
    const onDurationChange = () => {
      events.emit('durationchange', video.duration)
    }
    const onLoadStart = () => {
      mediaLoadStartedForCurrentSource = true
      mediaMetadataLoadedForCurrentSource = false
      loading = true
      events.emit('loadsstart', undefined)
    }
    const onLoadedMetadata = () => {
      if (!isNativeMediaSourceCurrent()) return
      mediaMetadataLoadedForCurrentSource = true
      events.emit('loadedmetadata', { duration: video.duration, videoWidth: video.videoWidth, videoHeight: video.videoHeight })
    }
    const onLoadedData = () => {
      if (!isNativeMediaSourceCurrent()) return
      events.emit('loadeddata', undefined)
    }
    const onProgress = () => {
      if (video.buffered.length > 0 && video.duration > 0) {
        const bufferedEnd = video.buffered.end(video.buffered.length - 1)
        bufferedProgress = (bufferedEnd / video.duration) * 100
        events.emit('progress', { buffered: video.buffered, duration: video.duration })
      }
    }
    const onVolumeChange = () => {
      const v = audioGainNode ? volume : video.volume * 100
      volume = v
      muted = video.muted
      void adapter.saveConfig({ volume: v, muted: video.muted })
      events.emit('volumechange', { volume: v / 100, muted: video.muted })
    }
    const onWaiting = () => {
      loading = true
      errorRecovery.scheduleWaitingRecovery()
      events.emit('waiting', undefined)
    }
    const onStalled = () => {
      events.emit('waiting', undefined)
    }
    const onCanPlay = () => {
      if (!canAcceptNativeCanPlay()) return
      loading = false
      retryCount = 0
      errorRecovery.clearWaitingRecovery()
      events.emit('canplay', undefined)

      if (autoPlayOnReady) {
        autoPlayOnReady = false
        void play().catch((e) => {
          logger.warn('[PlayerEngine] Auto-play failed after canplay', e)
        })
      }
    }
    const onError = (e: Event) => {
      if (pluginHandlingError) {
        logger.debug('[PlayerEngine] Skipping native error, plugin is already handling recovery')
        return
      }

      errorRecovery.clearWaitingRecovery()
      const mediaErrorCode = videoElement?.error?.code
      const errorCode = mediaErrorCode === MediaError.MEDIA_ERR_NETWORK
        ? 'NETWORK_ERROR'
        : mediaErrorCode === MediaError.MEDIA_ERR_DECODE
          ? 'MEDIA_DECODE_ERROR'
          : mediaErrorCode === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED
            ? 'MEDIA_NOT_SUPPORTED'
            : 'MEDIA_ERROR'
      const err: PlayerError = {
        code: errorCode,
        message: 'Video playback error',
        fatal: true,
        details: e
      }
      void errorRecovery.handleRecoveryError(err)
        .then((recovered) => {
          if (!recovered) errorRecovery.reportFatalError(err)
        })
        .catch((e) => {
          logger.warn('[PlayerEngine] Error recovery chain failed', e)
          errorRecovery.reportFatalError(err)
        })
    }
    const onEnterPiP = () => {
      events.emit('enterpictureinpicture', undefined)
    }
    const onLeavePiP = () => {
      events.emit('leavepictureinpicture', undefined)
    }

    video.addEventListener('play', onPlay)
    video.addEventListener('playing', onPlaying)
    video.addEventListener('pause', onPause)
    video.addEventListener('ended', onEnded)
    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('durationchange', onDurationChange)
    video.addEventListener('loadstart', onLoadStart)
    video.addEventListener('loadedmetadata', onLoadedMetadata)
    video.addEventListener('loadeddata', onLoadedData)
    video.addEventListener('progress', onProgress)
    video.addEventListener('volumechange', onVolumeChange)
    video.addEventListener('waiting', onWaiting)
    video.addEventListener('stalled', onStalled)
    video.addEventListener('canplay', onCanPlay)
    video.addEventListener('error', onError)
    video.addEventListener('enterpictureinpicture', onEnterPiP)
    video.addEventListener('leavepictureinpicture', onLeavePiP)

    removeVideoListeners = () => {
      video.removeEventListener('play', onPlay)
      video.removeEventListener('playing', onPlaying)
      video.removeEventListener('pause', onPause)
      video.removeEventListener('ended', onEnded)
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('durationchange', onDurationChange)
      video.removeEventListener('loadstart', onLoadStart)
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
      video.removeEventListener('loadeddata', onLoadedData)
      video.removeEventListener('progress', onProgress)
      video.removeEventListener('volumechange', onVolumeChange)
      video.removeEventListener('waiting', onWaiting)
      video.removeEventListener('stalled', onStalled)
      video.removeEventListener('canplay', onCanPlay)
      video.removeEventListener('error', onError)
      video.removeEventListener('enterpictureinpicture', onEnterPiP)
      video.removeEventListener('leavepictureinpicture', onLeavePiP)
      removeVideoListeners = null
    }
  }

  const handleFullscreenChange = (): void => {
    if (typeof document === 'undefined') return
    events.emit('fullscreenchange', !!document.fullscreenElement)
  }

  const init = async (): Promise<void> => {
    if (destroyed) return

    try {
      config = await adapter.loadConfig()
    } catch (e) {
      logger.warn('[PlayerEngine] Failed to load user config', e)
      config = {}
    }

    applyConfig(config)
    await initPlugins()

    if (typeof document !== 'undefined') {
      document.addEventListener('fullscreenchange', handleFullscreenChange)
    }

    setupVideoListeners()
    applyMediaSettings(videoElement)
  }

  const destroy = (): void => {
    if (destroyed) return
    destroyed = true

    if (removeVideoListeners) {
      removeVideoListeners()
    }

    errorRecovery.clearWaitingRecovery()
    if (typeof document !== 'undefined') {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }
    audioSourceNode?.disconnect()
    audioGainNode?.disconnect()
    void audioContext?.close()

    flushProgress()
    pluginManager.destroy()
    releaseVideoElementMedia(videoElement)
    events.destroy()
  }

  const attachVideoElement = (el: HTMLVideoElement | null): void => {
    if (videoElement === el) return
    const previousVideoElement = videoElement

    if (removeVideoListeners) {
      removeVideoListeners()
    }

    errorRecovery.clearWaitingRecovery()
    releaseVideoElementMedia(previousVideoElement)
    videoElement = el
    setupVideoListeners()
    applyMediaSettings(videoElement)

    if (inited && pendingSource) {
      const source = pendingSource
      pendingSource = null
      doLoadSource(source)
    }
  }

  const attachContainerElement = (el: HTMLElement | null): void => {
    containerElement = el
  }

  const play = async (): Promise<boolean> => {
    if (!videoElement) return false
    try {
      if (audioContext?.state === 'suspended') {
        await audioContext.resume()
      }
      await videoElement.play()
      return true
    } catch (e) {
      logger.warn('[PlayerEngine] Play failed', e)
      return false
    }
  }

  const pause = (): void => {
    if (!videoElement) return
    videoElement.pause()
  }

  const seek = (time: number): void => {
    if (!videoElement) return
    errorRecovery.clearWaitingRecovery()
    errorRecovery.suppressWaitingRecovery(Math.max(retryDelay * 2, 4000))
    videoElement.currentTime = time
    events.emit('seeking', time)
    adapter.trackEvent?.('seek', { currentTime: time, duration: videoElement.duration })
  }

  const setVolume = (vol: number): void => {
    const v = Math.max(0, Math.min(MAX_VOLUME, vol))
    const shouldUnmute = v > 0 && muted
    volume = v
    if (shouldUnmute) muted = false

    if (videoElement) {
      applyMediaSettings(videoElement)
      if (shouldUnmute) {
        videoElement.muted = false
      }
    }

    events.emit('volumechange', { volume: v / 100, muted })
    void adapter.saveConfig({ volume: v, muted })
    adapter.trackEvent?.('volumechange', { volume: v, muted })
  }

  const setMuted = (value: boolean): void => {
    muted = value
    if (videoElement) {
      videoElement.muted = value
    }
    events.emit('volumechange', { volume: volume / 100, muted })
    void adapter.saveConfig({ muted: value })
  }

  const toggleMute = (): void => {
    setMuted(!muted)
  }

  const setPlaybackRate = (rate: number): void => {
    playbackRate = rate
    if (videoElement) {
      videoElement.playbackRate = rate
    }
    events.emit('ratechange', rate)
    void adapter.saveConfig({ playbackRate: rate })
  }

  const setLoop = (value: boolean): void => {
    loop = value
    if (videoElement) {
      videoElement.loop = value
    }
    void adapter.saveConfig({ loop: value })
  }

  const setAutoplay = (value: boolean): void => {
    autoplay = value
    void adapter.saveConfig({ autoplay: value })
  }

  const setAutoplayNext = (value: boolean): void => {
    autoplayNext = value
    void adapter.saveConfig({ autoplayNext: value })
  }

  const isAutoQualityToken = (quality: QualitySelectionRequest): boolean => {
    if (typeof quality !== 'string' && typeof quality !== 'number') return false
    const qStr = String(quality).toLowerCase()
    return quality === 'auto' || quality === -1 || qStr === 'auto' || qStr === '自动'
  }

  const findQualityByRequest = (quality: QualitySelectionRequest): QualityLevel | null => {
    if (typeof quality !== 'string' && typeof quality !== 'number') return null
    const normalizedQuality = String(quality)
    return qualities.find(
      (item) => String(item.id) === normalizedQuality || item.label === normalizedQuality
    ) || null
  }

  const resolveQualitySelection = (quality: QualitySelectionRequest): {
    controllerQuality: QualitySelectionRequest
    emittedLabel: string
    isAutoQuality: boolean
  } => {
    if (isAutoQualityToken(quality)) {
      currentQualityId = null
      registeredQualityId = null
      currentQualityLabel = 'auto'
      return {
        controllerQuality: 'auto',
        emittedLabel: 'auto',
        isAutoQuality: true
      }
    }

    const matchedQuality = findQualityByRequest(quality)
    if (matchedQuality) {
      currentQualityId = matchedQuality.id
      registeredQualityId = matchedQuality.id
      currentQualityLabel = matchedQuality.label
    } else {
      currentQualityId = typeof quality === 'number' ? quality : null
      registeredQualityId = typeof quality === 'number' ? quality : null
      currentQualityLabel = String(quality)
    }

    return {
      controllerQuality: matchedQuality?.runtimeSelection ?? currentQualityId ?? quality,
      emittedLabel: currentQualityLabel || String(quality),
      isAutoQuality: false
    }
  }

  const setQuality = (quality: QualitySelectionRequest): void => {
    errorRecovery.suppressWaitingRecovery(Math.max(retryDelay * 2, 4000))
    const { controllerQuality, emittedLabel } = resolveQualitySelection(quality)

    const getQualityController = (): QualityController | null => {
      const preferredDashPlugin = currentSource?.playbackEngine === 'shaka' ? 'shaka-dash' : 'dash'
      if (currentSourceType === 'hls') return pluginManager.get<QualityController>('hls')
      if (currentSourceType === 'dash') return pluginManager.get<QualityController>(preferredDashPlugin)
      return pluginManager.get<QualityController>('shaka-dash') || pluginManager.get<QualityController>('dash') || pluginManager.get<QualityController>('hls')
    }

    const controller = getQualityController()
    if (controller && typeof controller.setQuality === 'function') {
      controller.setQuality(controllerQuality)
    }

    events.emit('qualitychange', { quality: emittedLabel, auto: emittedLabel === 'auto', id: currentQualityId ?? undefined })
    options.onQualityChange?.(emittedLabel)
    adapter.trackEvent?.('qualitychange', { quality: emittedLabel, auto: emittedLabel === 'auto' })
  }

  const toggleFullscreen = async (): Promise<void> => {
    if (!containerElement) return
    if (typeof document === 'undefined') return

    try {
      if (!document.fullscreenElement) {
        await containerElement.requestFullscreen()
      } else {
        await document.exitFullscreen()
      }
      events.emit('fullscreenchange', !!document.fullscreenElement)
    } catch (e) {
      logger.warn('[PlayerEngine] Fullscreen failed', e)
    }
  }

  const togglePictureInPicture = async (): Promise<void> => {
    if (!videoElement) return
    if (typeof document === 'undefined') return

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture()
      } else {
        await videoElement.requestPictureInPicture()
      }
    } catch (e) {
      logger.warn('[PlayerEngine] PiP failed', e)
    }
  }

  const setSubtitleTracks = async (tracks: SubtitleTrack[]): Promise<void> => {
    subtitleTracks = tracks
    if (tracks.length === 0) {
      currentSubtitle = null
    }

    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.setTracks === 'function') {
      await subtitlesPlugin.setTracks(tracks)
    }
  }

  const setSubtitle = (track: SubtitleTrack | null): void => {
    currentSubtitle = track
    const requestId = ++subtitleLoadRequestId
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')

    if (subtitlesPlugin) {
      if (track && typeof subtitlesPlugin.loadTrack === 'function') {
        void Promise.resolve(subtitlesPlugin.loadTrack(track))
          .then((loaded) => {
            if (requestId !== subtitleLoadRequestId) return
            if (loaded !== false && typeof subtitlesPlugin.enable === 'function') {
              subtitlesPlugin.enable()
              return
            }
            if (typeof subtitlesPlugin.disable === 'function') {
              subtitlesPlugin.disable()
            }
          })
          .catch((error) => {
            logger.warn('[PlayerEngine] Failed to load subtitle track', error)
            if (requestId !== subtitleLoadRequestId) return
            if (typeof subtitlesPlugin.disable === 'function') {
              subtitlesPlugin.disable()
            }
          })
      } else if (!track && typeof subtitlesPlugin.disable === 'function') {
        subtitlesPlugin.disable()
      }
    }

    saveConfigPatch({
      subtitleEnabled: !!track,
      subtitleTrackId: track?.id,
      subtitleLanguage: track?.language,
    })
  }

  const getSubtitleStyle = (): Record<string, unknown> => {
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.exportStyle === 'function') {
      return subtitlesPlugin.exportStyle()
    }
    return {}
  }

  const applySubtitlePreset = (presetId: string): void => {
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.applyPreset === 'function') {
      subtitlesPlugin.applyPreset(presetId)
    }
  }

  const setSubtitleOffset = (offsetSeconds: number): void => {
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.setSubtitleOffset === 'function') {
      subtitlesPlugin.setSubtitleOffset(offsetSeconds)
    }
  }

  const getSubtitleOffset = (): number => {
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.getSubtitleOffset === 'function') {
      return subtitlesPlugin.getSubtitleOffset()
    }
    return 0
  }

  const setSubtitleStyle = (style: Record<string, unknown>): void => {
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.importStyle === 'function') {
      subtitlesPlugin.importStyle(style)
    }
  }

  const toggleSubtitles = (): void => {
    const subtitlesPlugin = pluginManager.get<SubtitleController>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.toggle === 'function') {
      subtitlesPlugin.toggle()
    }
  }

  const buildProgress = (): PlaybackProgress | null => {
    const key = progressKey
    if (!key) return null
    if (!videoElement) return null
    if (!isFinite(videoElement.duration) || videoElement.duration <= 0) return null

    const current = videoElement.currentTime
    const duration = videoElement.duration

    return {
      progressKey: key,
      currentTime: current,
      duration,
      progress: duration > 0 ? (current / duration) * 100 : 0,
      timestamp: Date.now()
    }
  }

  const commitProgress = (progress: PlaybackProgress): void => {
    void adapter.saveProgress(progress).catch((e) => {
      logger.warn('[PlayerEngine] Failed to save progress', e)
    })
    lastSavedTime = progress.currentTime
    lastSavedAt = Date.now()
  }

  const scheduleProgressSave = (): void => {
    const progress = buildProgress()
    if (!progress) return

    if (Math.abs(progress.currentTime - lastSavedTime) < progressThreshold) return

    const now = Date.now()
    if (now - lastSavedAt >= progressSaveInterval) {
      commitProgress(progress)
      return
    }

    pendingProgress = progress
    if (saveTimer) return

    const delay = Math.max(0, progressSaveInterval - (now - lastSavedAt))
    saveTimer = setTimeout(() => {
      saveTimer = null
      if (!pendingProgress) return
      commitProgress(pendingProgress)
      pendingProgress = null
    }, delay)
  }

  const flushProgress = (): void => {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }

    const progress = pendingProgress || buildProgress()
    pendingProgress = null
    if (!progress) return

    if (Math.abs(progress.currentTime - lastSavedTime) < progressThreshold) return
    commitProgress(progress)
  }

  const saveProgress = (): void => {
    scheduleProgressSave()
  }

  const loadProgress = async (key: string): Promise<number | null> => {
    const progress = await adapter.loadProgress(key)
    return progress?.currentTime ?? null
  }

  const getStats = (): PlayerStats => {
    const video = videoElement as (HTMLVideoElement & { webkitDroppedFrameCount?: number; webkitDecodedFrameCount?: number }) | null
    const webkitDropped = video?.webkitDroppedFrameCount
    const webkitDecoded = video?.webkitDecodedFrameCount
    return {
      resolution: video && video.videoWidth > 0
        ? { width: video.videoWidth, height: video.videoHeight }
        : null,
      codec: currentQualityLabel,
      sourceType: currentSourceType,
      bufferedPercent: bufferedProgress,
      playbackRate: video?.playbackRate ?? playbackRate,
      quality: currentQualityLabel,
      volume: volume,
      muted,
      duration: video?.duration ?? 0,
      currentTime: video?.currentTime ?? 0,
      droppedFrames: typeof webkitDropped === 'number' ? webkitDropped : 0,
      totalFrames: typeof webkitDecoded === 'number' ? webkitDecoded : 0,
      videoBitrate: null,
      audioBitrate: null,
    }
  }

  return {
    attachVideoElement,
    attachContainerElement,

    init,
    destroy,

    play,
    pause,
    seek,
    setVolume,
    setMuted,
    toggleMute,
    setPlaybackRate,
    setLoop,
    setAutoplay,
    setAutoplayNext,

    setQuality,

    toggleFullscreen,
    togglePictureInPicture,

    loadSource,
    getSource: () => currentSource,
    getSourceType: () => currentSourceType,

    setSubtitleTracks,
    setSubtitle,
    toggleSubtitles,
    getSubtitleStyle,
    setSubtitleStyle,
    applySubtitlePreset,
    setSubtitleOffset,
    getSubtitleOffset,

    saveProgress,
    loadProgress,

    getConfig: () => ({ ...config }),
    getQualities: () => qualities,
    getCurrentQualityLabel: () => currentQualityLabel,
    getCurrentQualityId: () => currentQualityId,
    getSubtitleTracks: () => subtitleTracks,
    getCurrentSubtitle: () => currentSubtitle,

    getPlugin: <T>(name: string) => pluginManager.get(name) as T,
    getStats,
    on: events.on.bind(events),
    off: events.off.bind(events)
  }
}

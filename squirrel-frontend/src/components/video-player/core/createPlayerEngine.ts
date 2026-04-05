import { EventEmitter } from './EventEmitter'
import { PluginManager } from './PluginManager'
import { MemoryAdapter, type IPlayerAdapter, type UserConfig, type PlaybackProgress } from './PlayerAdapter'
import { playerLogger } from './logger'
import type {
  MediaSource,
  PlayerError,
  PlayerEvents,
  PlayerState,
  QualityLevel,
  PluginConfig,
  PluginContext,
  SubtitleTrack,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext
} from './types'

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

  play: () => Promise<void>
  pause: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  setMuted: (muted: boolean) => void
  toggleMute: () => void
  setPlaybackRate: (rate: number) => void
  setLoop: (loop: boolean) => void
  setAutoplay: (autoplay: boolean) => void
  setAutoplayNext: (autoplayNext: boolean) => void

  setQuality: (quality: string | number) => void

  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>

  loadSource: (source: MediaSource) => void
  getSource: () => MediaSource | null
  getSourceType: () => 'native' | 'hls' | 'dash' | null

  setSubtitleTracks: (tracks: SubtitleTrack[]) => void
  setSubtitle: (track: SubtitleTrack | null) => void
  toggleSubtitles: () => void

  saveProgress: () => void
  loadProgress: (progressKey: string) => Promise<number | null>

  getConfig: () => UserConfig
  getQualities: () => QualityLevel[]
  getCurrentQualityLabel: () => string | null
  getCurrentQualityId: () => string | number | null
  getSubtitleTracks: () => SubtitleTrack[]
  getCurrentSubtitle: () => SubtitleTrack | null

  getPlugin: <T>(name: string) => T | null
  on: EventEmitter<PlayerEvents>['on']
  off: EventEmitter<PlayerEvents>['off']
}

const detectSourceType = (src: string): 'hls' | 'dash' | 'native' => {
  const url = src.toLowerCase()
  if (url.includes('.m3u8') || url.includes('format=m3u8')) return 'hls'
  if (url.includes('.mpd') || url.includes('/mpd') || url.includes('format=mpd')) return 'dash'
  return 'native'
}

export function createPlayerEngine(options: PlayerEngineOptions = {}): PlayerEngine {
  const logger = playerLogger
  const adapter = options.adapter ?? new MemoryAdapter()

  const events = new EventEmitter<PlayerEvents>()
  const pluginManager = new PluginManager(events)

  let videoElement: HTMLVideoElement | null = null
  let containerElement: HTMLElement | null = null

  let inited = false
  let destroyed = false

  let config: UserConfig = {}

  let autoplay = !!options.autoplay
  let autoplayNext = options.autoplayNext !== false
  let muted = !!options.muted
  let volume = typeof options.volume === 'number' ? options.volume : 100
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

  let progressKey: string | null = null

  let currentSource: MediaSource | null = null
  let currentSourceType: 'native' | 'hls' | 'dash' | null = null
  let currentSourceKey = ''
  let pendingSource: MediaSource | null = null
  let pendingSourceKey = ''
  let autoPlayOnReady = false

  let lastSavedTime = 0
  let lastSavedAt = 0
  let pendingProgress: PlaybackProgress | null = null
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  const progressSaveInterval = options.progress?.saveInterval ?? 2000
  const progressThreshold = options.progress?.thresholdSeconds ?? 5

  const maxRetries = options.errorRecovery?.maxRetries ?? 3
  const retryDelay = options.errorRecovery?.retryDelay ?? 2000
  const enableQualityFallback = options.errorRecovery?.enableQualityFallback ?? true

  let isRecovering = false
  let retryCount = 0
  let waitingRecoveryTimer: ReturnType<typeof setTimeout> | null = null
  let waitingRecoverySuppressedUntil = 0

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

  const clearWaitingRecovery = (): void => {
    if (!waitingRecoveryTimer) return
    clearTimeout(waitingRecoveryTimer)
    waitingRecoveryTimer = null
  }

  const scheduleWaitingRecovery = (): void => {
    clearWaitingRecovery()
    const stalledAtTime = videoElement?.currentTime ?? 0
    const suppressionDelay = Math.max(0, waitingRecoverySuppressedUntil - Date.now())
    waitingRecoveryTimer = setTimeout(() => {
      waitingRecoveryTimer = null
      if (!videoElement || !loading || videoElement.ended) return
      if (Math.abs((videoElement.currentTime ?? 0) - stalledAtTime) > 0.25) return

      const err: PlayerError = {
        code: 'STALL_DETECTED',
        message: 'Playback stalled while waiting for media',
        fatal: false,
      }
      void handleRecoveryError(err)
        .then((recovered) => {
          if (!recovered) reportFatalError(err)
        })
        .catch(() => reportFatalError(err))
    }, Math.max(retryDelay, 1500) + suppressionDelay)
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
      volume: video?.volume ?? (volume / 100),
      muted: video?.muted ?? muted,
      playbackRate: video?.playbackRate ?? playbackRate,
      fullscreen: typeof document !== 'undefined' ? !!document.fullscreenElement : false,
      pip: typeof document !== 'undefined' ? document.pictureInPictureElement === video : false,
      quality: currentQualityLabel,
      autoQuality: currentQualityLabel === 'auto'
    }
  }

  const applyMediaSettings = (el: HTMLVideoElement | null): void => {
    if (!el) return
    el.volume = Math.max(0, Math.min(1, volume / 100))
    el.muted = muted
    el.playbackRate = playbackRate
    el.loop = loop
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
    if (hasVolume) volume = next.volume as number
    if (hasMuted) muted = next.muted as boolean
    if (hasPlaybackRate) playbackRate = next.playbackRate as number

    applyMediaSettings(videoElement)
  }

  const reportFatalError = (error: PlayerError): void => {
    loading = false
    events.emit('error', error)
    options.onError?.(error)
  }

  const setRecoveryQualities = (qs: QualityLevel[]): void => {
    qualities = qs
    retryCount = 0
  }

  const getNextLowerQuality = (): QualityLevel | null => {
    const sorted = [...qualities].sort((a, b) => (b.height || 0) - (a.height || 0))
    const currentId = registeredQualityId
    const currentInSorted = sorted.findIndex(q => q.id === currentId)
    if (currentInSorted >= 0 && currentInSorted < sorted.length - 1) {
      return sorted[currentInSorted + 1]
    }
    if (currentInSorted === -1 && sorted.length > 1) {
      return sorted[sorted.length - 1]
    }
    return null
  }

  const determineRecoveryStrategy = (error: PlayerError): 'retry' | 'quality-fallback' | 'none' => {
    const code = String(error.code || '')

    if (code.includes('NOT_SUPPORTED') || code.includes('CAPABILITY')) {
      return 'none'
    }

    if (code.includes('NETWORK') || code.includes('TIMEOUT')) {
      if (retryCount < maxRetries) return 'retry'
      if (enableQualityFallback && getNextLowerQuality()) return 'quality-fallback'
    }

    if (code.includes('MEDIA') || code.includes('DECODE') || code.includes('BUFFER') || code.includes('STALL')) {
      if (enableQualityFallback && getNextLowerQuality()) return 'quality-fallback'
    }

    if (!error.fatal && retryCount < maxRetries) return 'retry'
    if (error.fatal && retryCount < maxRetries) return 'retry'
    return 'none'
  }

  const executeQualityFallback = (): boolean => {
    const nextQuality = getNextLowerQuality()
    if (!nextQuality) return false

    logger.debug(`[ErrorRecovery] Falling back to quality: ${nextQuality.label}`)
    retryCount = 0
    setQuality(nextQuality.id ?? nextQuality.label)
    return true
  }

  const getStreamController = (): any => {
    if (currentSourceType === 'hls') return pluginManager.get<any>('hls')
    if (currentSourceType === 'dash') return pluginManager.get<any>('dash')
    return pluginManager.get<any>('dash') || pluginManager.get<any>('hls')
  }

  const buildRecoveryContext = (): PlaybackRecoveryContext => ({
    retryCount,
    maxRetries,
    retryDelay,
    source: currentSource ? { ...currentSource } : null,
    currentTime: videoElement?.currentTime ?? 0,
    wasPlaying: !!videoElement && !videoElement.paused && !videoElement.ended
  })

  const reloadCurrentSource = (): boolean => {
    if (!currentSource) return false

    const sourceToReload = { ...currentSource }
    const resumeTime = videoElement?.currentTime ?? 0
    const shouldResumePlayback = !!videoElement && !videoElement.paused && !videoElement.ended

    if (videoElement && Number.isFinite(resumeTime) && resumeTime > 0) {
      videoElement.addEventListener('loadedmetadata', () => {
        if (!videoElement) return
        const nextTime = Number.isFinite(videoElement.duration) && videoElement.duration > 0
          ? Math.min(resumeTime, videoElement.duration)
          : resumeTime
        try {
          videoElement.currentTime = Math.max(0, nextTime)
        } catch (error) {
          logger.warn('[ErrorRecovery] Failed to restore playback position after reload', error)
        }
      }, { once: true })
    }

    currentSourceKey = ''
    pendingSourceKey = ''
    doLoadSource(sourceToReload)

    if (shouldResumePlayback) {
      autoPlayOnReady = true
    }

    logger.debug('[ErrorRecovery] Reloaded current source')
    return true
  }

  const executeRetry = async (error: PlayerError): Promise<boolean> => {
    retryCount += 1
    logger.debug(`[ErrorRecovery] Retry attempt ${retryCount}/${maxRetries}`)
    await new Promise((resolve) => setTimeout(resolve, retryDelay))

    const controller = getStreamController()
    const recoveryAction: PlaybackRecoveryAction =
      typeof controller?.recoverPlayback === 'function'
        ? await controller.recoverPlayback(error, {
            ...buildRecoveryContext(),
            retryCount
          })
        : 'reload-source'

    if (recoveryAction === 'handled') {
      return true
    }

    if (recoveryAction === 'reload-source') {
      return reloadCurrentSource()
    }

    return false
  }

  const handleRecoveryError = async (error: PlayerError): Promise<boolean> => {
    if (isRecovering) {
      logger.debug('[ErrorRecovery] Already recovering, skipping')
      return false
    }

    isRecovering = true
    try {
      const strategy = determineRecoveryStrategy(error)
      logger.debug(`[ErrorRecovery] Strategy: ${strategy}, Error`, error)

      if (strategy === 'retry') {
        return await executeRetry(error)
      }

      if (strategy === 'quality-fallback') {
        return executeQualityFallback()
      }

      return false
    } finally {
      isRecovering = false
    }
  }

  const createPluginContext = (): PluginContext => ({
    get videoElement() { return videoElement },
    get state() { return getState() },
    logger,

    on: events.on.bind(events),
    off: events.off.bind(events),
    emit(event, payload) {
      if (event === 'waiting') {
        loading = true
        scheduleWaitingRecovery()
      }

      if (event === 'canplay') {
        loading = false
        retryCount = 0
        clearWaitingRecovery()

        if (autoPlayOnReady) {
          autoPlayOnReady = false
          void play().catch(() => {})
        }
      }

      events.emit(event, payload)
    },
    once: events.once.bind(events),

    async play() { await play() },
    pause() { pause() },
    seek(time) { seek(time) },
    setVolume(v) { setVolume(v * 100) },
    setMuted(m) { setMuted(m) },
    setPlaybackRate(r) { setPlaybackRate(r) },

    setQuality(q) { setQuality(q) },
    getQualities() { return qualities },
    registerQualities(qs) {
      qualities = qs
      setRecoveryQualities(qs)
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
      void handleRecoveryError(error)
        .then((recovered) => {
          if (!recovered) reportFatalError(error)
        })
        .catch(() => reportFatalError(error))
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

    try {
      videoElement.pause()
    } catch {}

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

    if (source.poster && videoElement) {
      videoElement.poster = source.poster
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
    loading = true
    clearWaitingRecovery()
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
      clearWaitingRecovery()
      events.emit('play', undefined)
      options.onPlay?.()
    }
    const onPause = () => {
      clearWaitingRecovery()
      flushProgress()
      events.emit('pause', undefined)
      options.onPause?.()
    }
    const onEnded = () => {
      clearWaitingRecovery()
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
    const onLoadedMetadata = () => {
      events.emit('loadedmetadata', { duration: video.duration, videoWidth: video.videoWidth, videoHeight: video.videoHeight })
    }
    const onProgress = () => {
      if (video.buffered.length > 0 && video.duration > 0) {
        const bufferedEnd = video.buffered.end(video.buffered.length - 1)
        bufferedProgress = (bufferedEnd / video.duration) * 100
        events.emit('progress', { buffered: video.buffered, duration: video.duration })
      }
    }
    const onVolumeChange = () => {
      const v = video.volume * 100
      volume = v
      muted = video.muted
      void adapter.saveConfig({ volume: v, muted: video.muted })
      events.emit('volumechange', { volume: v / 100, muted: video.muted })
    }
    const onWaiting = () => {
      loading = true
      scheduleWaitingRecovery()
      events.emit('waiting', undefined)
    }
    const onStalled = () => {
      loading = true
      scheduleWaitingRecovery()
      events.emit('waiting', undefined)
    }
    const onCanPlay = () => {
      loading = false
      retryCount = 0
      clearWaitingRecovery()
      events.emit('canplay', undefined)

      if (autoPlayOnReady) {
        autoPlayOnReady = false
        void play().catch(() => {})
      }
    }
    const onError = (e: Event) => {
      clearWaitingRecovery()
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
      void handleRecoveryError(err)
        .then((recovered) => {
          if (!recovered) reportFatalError(err)
        })
        .catch(() => reportFatalError(err))
    }
    const onEnterPiP = () => {
      events.emit('enterpictureinpicture', undefined)
    }
    const onLeavePiP = () => {
      events.emit('leavepictureinpicture', undefined)
    }

    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)
    video.addEventListener('ended', onEnded)
    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('durationchange', onDurationChange)
    video.addEventListener('loadedmetadata', onLoadedMetadata)
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
      video.removeEventListener('pause', onPause)
      video.removeEventListener('ended', onEnded)
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('durationchange', onDurationChange)
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
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
    } catch {
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

    clearWaitingRecovery()
    if (typeof document !== 'undefined') {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }

    flushProgress()

    pluginManager.destroy()
    events.destroy()
  }

  const attachVideoElement = (el: HTMLVideoElement | null): void => {
    if (videoElement === el) return

    if (removeVideoListeners) {
      removeVideoListeners()
    }

    clearWaitingRecovery()
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

  const play = async (): Promise<void> => {
    if (!videoElement) return
    try {
      await videoElement.play()
    } catch (e) {
      logger.warn('[PlayerEngine] Play failed', e)
    }
  }

  const pause = (): void => {
    if (!videoElement) return
    videoElement.pause()
  }

  const seek = (time: number): void => {
    if (!videoElement) return
    videoElement.currentTime = time
    events.emit('seeking', time)
  }

  const setVolume = (vol: number): void => {
    const v = Math.max(0, Math.min(100, vol))
    const shouldUnmute = v > 0 && muted
    volume = v
    if (shouldUnmute) muted = false

    if (videoElement) {
      videoElement.volume = v / 100
      if (shouldUnmute) {
        videoElement.muted = false
      }
    }

    events.emit('volumechange', { volume: v / 100, muted })
    void adapter.saveConfig({ volume: v, muted })
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

  const setQuality = (quality: string | number): void => {
    waitingRecoverySuppressedUntil = Date.now() + Math.max(retryDelay * 2, 4000)

    const qStr = String(quality).toLowerCase()
    const isAutoQuality = quality === 'auto' || quality === -1 || qStr === 'auto' || qStr === '自动'

    if (isAutoQuality) {
      currentQualityId = null
      registeredQualityId = null
      currentQualityLabel = 'auto'
    } else {
      const directMatch = qualities.find(
        (item) => String(item.id) === String(quality) || item.label === String(quality)
      )
      if (directMatch) {
        currentQualityId = directMatch.id
        registeredQualityId = directMatch.id
        currentQualityLabel = directMatch.label
      } else {
        if (typeof quality === 'number') {
          currentQualityId = quality
          registeredQualityId = quality
        }
        currentQualityLabel = String(quality)
      }
    }

    if (!isAutoQuality && currentQualityId === null && typeof quality !== 'number') {
      const labelMatch = qualities.find((item) => item.label === String(quality))
      if (labelMatch) {
        currentQualityId = labelMatch.id
        registeredQualityId = labelMatch.id
        currentQualityLabel = labelMatch.label
      }
    }

    const getQualityController = (): any => {
      if (currentSourceType === 'hls') return pluginManager.get<any>('hls')
      if (currentSourceType === 'dash') return pluginManager.get<any>('dash')
      return pluginManager.get<any>('dash') || pluginManager.get<any>('hls')
    }

    const controllerQuality = isAutoQuality ? 'auto' : (currentQualityId ?? quality)
    const controller = getQualityController()
    if (controller && typeof controller.setQuality === 'function') {
      controller.setQuality(controllerQuality)
    }

    const emittedLabel = currentQualityLabel || String(quality)
    events.emit('qualitychange', { quality: emittedLabel, auto: emittedLabel === 'auto', id: currentQualityId ?? undefined })
    options.onQualityChange?.(emittedLabel)
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

  const setSubtitleTracks = (tracks: SubtitleTrack[]): void => {
    subtitleTracks = tracks
    const subtitlesPlugin = pluginManager.get<any>('subtitles')
    if (subtitlesPlugin && typeof subtitlesPlugin.setTracks === 'function') {
      subtitlesPlugin.setTracks(tracks)
    }
  }

  const setSubtitle = (track: SubtitleTrack | null): void => {
    currentSubtitle = track
    const subtitlesPlugin = pluginManager.get<any>('subtitles')

    if (subtitlesPlugin) {
      if (track && typeof subtitlesPlugin.loadTrack === 'function') {
        void subtitlesPlugin.loadTrack(track)
      }

      if (track && typeof subtitlesPlugin.enable === 'function') {
        subtitlesPlugin.enable()
      } else if (!track && typeof subtitlesPlugin.disable === 'function') {
        subtitlesPlugin.disable()
      }
    }
  }

  const toggleSubtitles = (): void => {
    const subtitlesPlugin = pluginManager.get<any>('subtitles')
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

    saveProgress,
    loadProgress,

    getConfig: () => ({ ...config }),
    getQualities: () => qualities,
    getCurrentQualityLabel: () => currentQualityLabel,
    getCurrentQualityId: () => currentQualityId,
    getSubtitleTracks: () => subtitleTracks,
    getCurrentSubtitle: () => currentSubtitle,

    getPlugin: <T>(name: string) => pluginManager.get(name) as T,
    on: events.on.bind(events),
    off: events.off.bind(events)
  }
}

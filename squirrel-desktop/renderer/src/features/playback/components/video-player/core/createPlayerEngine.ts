/**
 * Player engine factory.
 *
 * PlaybackCoordinator owns lifecycle and intent. This module composes the DOM
 * media element, stream drivers, recovery, plugins, persistence, and events
 * around that authority; none of those layers owns a parallel loading/error
 * state. See renderer/docs/adr/0003-coordinated-playback-lifecycle.md.
 */

import { EventEmitter } from './EventEmitter'
import { PluginManager } from './PluginManager'
import { LocalStorageAdapter, type UserConfig, type PlaybackProgress } from './PlayerAdapter'
import { playerLogger } from './logger'
import { createErrorRecovery, MAX_VOLUME, detectSourceType } from './error-recovery'
import { PlaybackCoordinator } from './PlaybackCoordinator'
import type { StreamAdapter, StreamAdapterType, StreamContext, StreamSeekResult } from './StreamAdapter'
import type { StreamSink } from './StreamSink'
import { HlsAdapter } from '../adapters/HlsAdapter'
import { DashAdapter } from '../adapters/DashAdapter'
import { ShakaDashAdapter } from '../adapters/ShakaDashAdapter'
import { errorMessage } from '@/shared/lib/errorMessage'
import type {
  MediaSource,
  PlayerError,
  PlayerEvents,
  PlayerState,
  PlayerStats,
  QualityLevel,
  QualitySelectionRequest,
  PluginContext,
  SubtitleStyle,
  SubtitleTrack,
} from './types'
import type {
  PlayerEngineOptions,
  PlayerEngine,
  SubtitleController,
} from './engine-types'

// Re-export the public types so existing `from './createPlayerEngine'` imports
// keep working without touching every call site.
export type { PlayerEngineOptions, PlayerEngine } from './engine-types'

export function createPlayerEngine(options: PlayerEngineOptions = {}): PlayerEngine {
  const logger = playerLogger
  // ponytail: LocalStorageAdapter is the real no-op baseline (persisted but
  // inert). The old MemoryAdapter existed only to give the ?? a non-null
  // default and was never wired in production (BackendPlayerAdapter is).
  const adapter = options.adapter ?? new LocalStorageAdapter()

  const events = new EventEmitter<PlayerEvents>()
  const pluginManager = new PluginManager(events)
  const coordinator = options.coordinator ?? new PlaybackCoordinator()
  const ownsCoordinator = !options.coordinator

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
  /** Last observed playhead used to distinguish real playback from a seek timeupdate. */
  let lastTimeUpdateMediaTime = Number.NaN
  let mediaLoadStartedForCurrentSource = false
  let mediaMetadataLoadedForCurrentSource = false
  let suppressMediaPauseIntent = false
  let suppressMediaLifecycle = false
  let pendingSeekOperationId: number | null = null

  // Stream adapter seam (see docs/adr/0001). The engine owns one adapter at a
  // time, keyed by currentAdapterType; loadSource reuses it when the source
  // type is unchanged and destroys + rebuilding it otherwise (A2 strategy).
  let currentStreamAdapter: StreamAdapter | null = null
  let currentAdapterType: StreamAdapterType | null = null
  let lastSavedTime = 0
  let lastSavedAt = 0
  let pendingProgress: PlaybackProgress | null = null
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  const progressSaveInterval = options.progress?.saveInterval ?? 2000
  const progressThreshold = options.progress?.thresholdSeconds ?? 5

  const maxRetries = options.errorRecovery?.maxRetries ?? 3
  const retryDelay = options.errorRecovery?.retryDelay ?? 2000
  // Default ON: high-bitrate YouTube/Bilibili DASH often stalls on the top
  // rung; stepping down is the primary mid-playback recovery path.
  const enableQualityFallback = options.errorRecovery?.enableQualityFallback ?? true

  let pluginHandlingError = false
  let retryCount = 0

  // dash.js and Shaka publish explicit bufferingStarted/bufferingCompleted state.
  // HlsAdapter intentionally relies on native <video> waiting/canplay events.
  const streamAdapterOwnsBuffering = (): boolean => {
    return currentAdapterType === 'dash' || currentAdapterType === 'shaka-dash'
  }

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
    const lifecycle = coordinator.getSnapshot()
    return {
      phase: lifecycle.phase,
      intent: lifecycle.intent,
      loadingStage: lifecycle.loadingStage,
      generation: lifecycle.generation,
      operationId: lifecycle.operationId,
      error: lifecycle.error,
      playing: lifecycle.phase === 'playing',
      paused: lifecycle.intent === 'pause',
      ended: lifecycle.phase === 'ended',
      waiting: lifecycle.loading,
      seeking: lifecycle.phase === 'seeking',
      currentTime: lifecycle.currentTime,
      duration: lifecycle.duration,
      buffered: lifecycle.bufferedPercent,
      volume: volume / 100,
      muted: video?.muted ?? muted,
      playbackRate: video?.playbackRate ?? playbackRate,
      fullscreen: typeof document !== 'undefined' ? !!document.fullscreenElement : false,
      pip: typeof document !== 'undefined' ? document.pictureInPictureElement === video : false,
      quality: currentQualityLabel,
      autoQuality: currentQualityLabel === 'auto'
    }
  }

  let lastNotifiedErrorKey = ''
  const removeCoordinatorListener = coordinator.subscribe((state) => {
    events.emit('statechange', getState())
    if (!state.error) return
    const errorKey = `${state.generation}:${state.operationId}:${state.error.code}`
    if (errorKey === lastNotifiedErrorKey) return
    lastNotifiedErrorKey = errorKey
    const error = state.error
    queueMicrotask(() => {
      const current = coordinator.getSnapshot()
      const currentKey = current.error
        ? `${current.generation}:${current.operationId}:${current.error.code}`
        : ''
      if (currentKey === errorKey) options.onError?.(error)
    })
  }, true)

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
    // Keep defaultPlaybackRate in sync so post-rebuffer restore (rate stuck at
    // Shaka's 0 starve flag) can recover the user-selected rate, not always 1.
    const rate = Number.isFinite(playbackRate) && playbackRate > 0 ? playbackRate : 1
    el.playbackRate = rate
    el.defaultPlaybackRate = rate
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
    mediaLoadStartedForCurrentSource = false
    mediaMetadataLoadedForCurrentSource = false
    events.emit('loadsstart', undefined)
  }

  /**
   * Native <video> canplay is only authoritative for progressive/native sources.
   * DASH buffering is owned by the stream adapter (Shaka/dash.js) via
   * loadingStateChanged — accepting native canplay mid-rebuffer against a stale
   * MSE attachment left the spinner out of sync (or cleared too early).
   * After DASH seek we still clear via: loadingStateChanged(false), seeked +
   * hasMediaAhead, playing, or timeupdate while media is ahead.
   */
  const canAcceptNativeCanPlay = (): boolean => {
    // Stream adapters drive canplay through loadingStateChanged.
    if (streamAdapterOwnsBuffering()) return false
    if (!isNativeMediaSourceCurrent()) return false
    if (!coordinator.getSnapshot().loading) return true
    return mediaLoadStartedForCurrentSource && mediaMetadataLoadedForCurrentSource
  }

  /**
   * True when the playhead already has enough buffered media to resume.
   *
   * FreeTube / official Shaka use rebufferingGoal ≈ 0.02s — the spinner must
   * clear as soon as a few frames exist at the NEW playhead. A 0.5s threshold
   * left store.loading stuck forever after scrub: Shaka was SATISFIED and
   * often already playing, but our probe still said "not ready".
   *
   * Do NOT use readyState alone as the sole signal: after scrub it can stay
   * HAVE_FUTURE_DATA against the pre-seek buffer while currentTime has jumped
   * to an unbuffered region. Always require a buffered range that covers the
   * current time (tiny ahead is enough).
   */
  const hasMediaAhead = (video: HTMLVideoElement, minAheadSec = 0.05): boolean => {
    try {
      const t = video.currentTime
      const { buffered } = video
      for (let i = 0; i < buffered.length; i += 1) {
        // Range must cover the playhead (small epsilon for float edges).
        if (buffered.start(i) <= t + 0.1 && buffered.end(i) >= t + minAheadSec) {
          return true
        }
      }
    } catch {
      // ignore buffer probe failures
    }
    return false
  }

  const errorRecovery = createErrorRecovery({
    getVideoElement: () => videoElement,
    getLoading: () => coordinator.getSnapshot().loading,
    setLoading: (v) => {
      if (v) {
        coordinator.markBuffering()
        return
      }
      clearLoadingState('error-recovery')
    },
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
    getPlaybackIntent: () => coordinator.getSnapshot().intent,
    setPlaybackIntent: (intent) => { coordinator.setIntent(intent) },
    getProgressKey: () => progressKey,
    getMaxRetries: () => maxRetries,
    getRetryDelay: () => retryDelay,
    getEnableQualityFallback: () => enableQualityFallback,
    events,
    getStreamAdapter: () => currentStreamAdapter,
    logger,
    adapter,
    onError: (error) => { coordinator.fail(error) },
    play: () => play(),
    setQuality: (q) => setQuality(q),
    doLoadSource: (s) => doLoadSource(s),
  })

  /** Clear engine + UI spinner together (store.loading only flips on canplay). */
  const clearLoadingState = (reason: string): void => {
    if (!coordinator.getSnapshot().loading) return
    const isActuallyPlaying = Boolean(videoElement && !videoElement.paused && !videoElement.ended)
    coordinator.markReady(isActuallyPlaying)
    retryCount = 0
    errorRecovery.clearWaitingRecovery()
    logger.debug(`[PlayerEngine] clearLoadingState (${reason})`)
    events.emit('canplay', undefined)
  }

  /** Run every plugin/native/adapter failure through one recovery transition. */
  const recoverFromError = async (error: PlayerError, origin: string): Promise<void> => {
    if (coordinator.getSnapshot().phase !== 'recovering') coordinator.beginRecovery()
    try {
      const recovered = await errorRecovery.handleRecoveryError(error)
      if (!recovered) {
        errorRecovery.reportFatalError(error)
        return
      }

      // Some soft recoveries complete synchronously without a buffering edge.
      // Do not leave the lifecycle in recovering when the landing already has
      // playable media; asynchronous recoveries settle via adapter/media events.
      const video = videoElement
      if (coordinator.getSnapshot().phase === 'recovering') {
        if (video && hasMediaAhead(video)) {
          coordinator.markReady(!video.paused && !video.ended)
        } else if (video) {
          coordinator.markBuffering()
          errorRecovery.scheduleWaitingRecovery()
        } else {
          errorRecovery.reportFatalError(error)
        }
      }
    } catch (recoveryError) {
      logger.warn(`[PlayerEngine] ${origin} recovery chain failed`, recoveryError)
      errorRecovery.reportFatalError(error)
    } finally {
      pluginHandlingError = false
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
        coordinator.markBuffering()
        errorRecovery.scheduleWaitingRecovery()
      }

      if (event === 'canplay') {
        coordinator.markReady(Boolean(videoElement && !videoElement.paused && !videoElement.ended))
        retryCount = 0
        errorRecovery.clearWaitingRecovery()

        if (coordinator.getSnapshot().intent === 'play') {
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
      // Same guard as StreamSink: never replace a non-empty ladder with [].
      publishQualities(Array.isArray(qs) ? qs : [], registeredQualityId)
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
      void recoverFromError(error, 'Plugin')
    },
    getPlugin<T>(name: string) { return pluginManager.get(name) as T }
  })

  /**
   * StreamContext handed to adapters at construction — narrow read-only input
   * (PR2: the reverse-driving surface that lived here in PR1 is gone; adapters
   * drive the engine only through the StreamSink passed to onSourceChange).
   */
  const createStreamContext = (): StreamContext => ({
    videoElement: () => videoElement,
    getState,
    logger,
  })

  /**
   * The engine's StreamSink implementation. This is the only channel by which
   * a stream adapter drives the engine (PR2, ADR-0001). Each callback maps to
   * the engine state machine that the old PluginContext emit/register helpers
   * used to mutate; the adapter no longer touches those directly.
   */
  const mapProviderQualities = (raw: MediaSource['qualities']): QualityLevel[] => {
    if (!Array.isArray(raw) || raw.length === 0) return []
    return raw
      .filter((item) => item && (item.id !== undefined && item.id !== null))
      .map((item) => {
        const id = item.id
        const height = typeof item.height === 'number' ? item.height : undefined
        const label = String(item.label || (height ? `${height}p` : id)).trim()
        return {
          id,
          label: label || String(id),
          width: item.width,
          height,
          bitrate: item.bitrate,
          codec: item.codec,
          src: item.src,
        }
      })
      .filter((item) => item.label.length > 0)
  }

  /** Keep usePlayer chip/menu in sync — label-only writes without this event leave "画质". */
  const emitQualityChange = (label: string | null, id: string | number | null, auto: boolean): void => {
    const emitted = label || (auto ? 'auto' : '')
    if (!emitted) return
    events.emit('qualitychange', {
      quality: emitted,
      auto,
      id: id ?? undefined,
    })
  }

  const publishQualities = (qs: QualityLevel[], currentId: string | number | null = null): void => {
    // Adapters can emit [] while the library is still attaching. Never wipe a
    // provider-seeded ladder with an empty list — that leaves only "画质".
    if (qs.length === 0 && qualities.length > 0) {
      if (currentId !== null) {
        registeredQualityId = currentId
        const match = qualities.find((item) => String(item.id) === String(currentId))
        if (match?.label) {
          currentQualityLabel = match.label
          currentQualityId = currentId
          emitQualityChange(match.label, currentId, false)
        }
      }
      return
    }

    qualities = qs
    errorRecovery.setRecoveryQualities(qs)
    events.emit('qualitiesloaded', qs)

    // Record the adapter's currently-playing quality (a fact), then apply the
    // engine's default-quality strategy on top (option 3, ADR-0001). The
    // strategy only fires when the engine has no recorded quality yet —
    // mirroring the old `!state.quality` guard. auto-quality is an engine
    // concern now, so there is no enableAutoQuality branch here.
    if (currentId !== null && currentId !== undefined) {
      registeredQualityId = currentId
      const match = qs.find((item) => String(item.id) === String(currentId))
      if (match) {
        const label = match.label || (match.height ? `${match.height}p` : String(match.id))
        currentQualityLabel = label
        currentQualityId = match.id
        emitQualityChange(label, match.id, false)
        return
      }
      // Adapter may report a runtime track id not present in provider hints.
      // Still surface a concrete height when the id looks like one (e.g. "1080").
      const idText = String(currentId)
      const heightFromId = Number.parseInt(idText.replace(/[^0-9]/g, ''), 10)
      if (Number.isFinite(heightFromId) && heightFromId >= 144) {
        const byHeight = qs.find((item) => Number(item.height || 0) === heightFromId)
        if (byHeight) {
          const label = byHeight.label || `${heightFromId}p`
          currentQualityLabel = label
          currentQualityId = byHeight.id
          registeredQualityId = byHeight.id
          emitQualityChange(label, byHeight.id, false)
          return
        }
        currentQualityLabel = `${heightFromId}p`
        currentQualityId = currentId
        emitQualityChange(currentQualityLabel, currentId, false)
        return
      }
    }

    // Keep ABR enabled for fast start, but never publish "auto" as the chip
    // label — users expect an explicit height. Prefer ~720p-class provisional
    // rung (matches Shaka defaultBandwidthEstimate) until adaptation reports.
    if (currentQualityId === null && qs.length > 0) {
      try {
        currentStreamAdapter?.setQuality('auto')
      } catch {
        // native / adapters without auto — leave selection to the library
      }
      const sorted = [...qs].sort(
        (a, b) => Number(b.height || 0) - Number(a.height || 0)
          || Number(b.bitrate || 0) - Number(a.bitrate || 0),
      )
      const provisional = sorted.find((item) => Number(item.height || 0) > 0 && Number(item.height || 0) <= 720)
        || sorted.find((item) => Number(item.height || 0) > 0)
        || sorted[0]
      if (provisional) {
        const label = provisional.label
          || (provisional.height ? `${provisional.height}p` : String(provisional.id))
        // Display-only: do not set currentQualityId so ABR stays unlocked and
        // the next adapter report can replace this with the real active track.
        currentQualityLabel = label
        emitQualityChange(label, null, true)
      }
    }
  }

  const createStreamSink = (generation: number): StreamSink => {
    const isActive = () => coordinator.getSnapshot().generation === generation
    return {
      qualitiesResolved: (qs, currentId) => {
        if (!isActive()) return
        publishQualities(Array.isArray(qs) ? qs : [], currentId)
      },

      qualityChanged: (quality) => {
        if (!isActive()) return
        registeredQualityId = quality.id
        currentQualityId = quality.id
        currentQualityLabel = quality.label
        events.emit('qualitychange', {
          quality: quality.label,
          auto: quality.auto,
          id: quality.id,
        })
        options.onQualityChange?.(quality.label)
      },

      loadingStateChanged: (isLoading) => {
        if (!isActive()) return
        if (isLoading) {
          if (!coordinator.getSnapshot().loading) {
            coordinator.markBuffering()
            errorRecovery.scheduleWaitingRecovery()
            events.emit('waiting', undefined)
          } else {
            errorRecovery.scheduleWaitingRecovery()
          }
          return
        }
        // Shaka can report SATISFIED while only audio is advancing. A seek
        // adapter with visual-completion support owns the final ready edge.
        if (pendingSeekOperationId !== null) {
          if (videoElement) ensurePlaybackRate(videoElement)
          return
        }
        clearLoadingState('stream-adapter')
        // Always undo rate=0 starve flag when the adapter reports not buffering,
        // even if the user had paused (pause should keep paused, not rate 0).
        if (videoElement) ensurePlaybackRate(videoElement)
        if (coordinator.getSnapshot().intent === 'play') {
          void play().catch((e) => {
            logger.warn('[PlayerEngine] Auto-play failed after canplay', e)
          })
        }
      },

      error: (error) => {
        if (!isActive()) return
        pluginHandlingError = true
        void recoverFromError(error, 'Stream adapter')
      },
    }
  }

  /**
   * Resolve which StreamAdapter a source needs, reusing the cached adapter when
   * the source type is unchanged and destroying + rebuilding it otherwise (A2).
   * Returns null for native sources (no adapter) or when the technology is
   * disabled. Mirrors the old "adapter instance lives, internal library instance
   * is rebuilt per source" semantics — note each adapter rebuilds its library
   * instance inside onSourceChange regardless.
   */
  const resolveStreamAdapter = (source: MediaSource): StreamAdapter | null => {
    const streamOpts = options.streamAdapters ?? {}
    const enableHls = streamOpts.enableHls !== false
    const enableDash = streamOpts.enableDash !== false

    let nextType: StreamAdapterType | null = null
    if (source.type === 'hls' && enableHls) {
      nextType = 'hls'
    } else if (source.type === 'dash' && enableDash) {
      nextType = source.playbackEngine === 'shaka' ? 'shaka-dash' : 'dash'
    }

    if (nextType === null) {
      if (currentStreamAdapter) {
        currentStreamAdapter.destroy()
        currentStreamAdapter = null
        currentAdapterType = null
      }
      return null
    }

    if (currentAdapterType === nextType && currentStreamAdapter) {
      return currentStreamAdapter
    }

    if (currentStreamAdapter) {
      currentStreamAdapter.destroy()
      currentStreamAdapter = null
      currentAdapterType = null
    }

    const ctx = createStreamContext()
    if (nextType === 'hls') {
      currentStreamAdapter = new HlsAdapter(ctx, streamOpts.hls)
    } else if (nextType === 'shaka-dash') {
      currentStreamAdapter = new ShakaDashAdapter(ctx, streamOpts['shaka-dash'])
    } else {
      currentStreamAdapter = new DashAdapter(ctx, streamOpts.dash)
    }
    currentAdapterType = nextType
    return currentStreamAdapter
  }

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

    lastTimeUpdateMediaTime = Number.NaN
    markSourceLoadingStarted()
    pluginHandlingError = false

    suppressMediaPauseIntent = true
    suppressMediaLifecycle = true
    releaseVideoElementMedia(videoElement)

    currentSourceKey = nextKey
    currentSource = source
    currentSourceType = (type === 'hls' || type === 'dash' || type === 'native') ? type : null
    pendingSourceKey = ''

    events.emit('sourcetypechange', currentSourceType)
    events.emit('sourcechange', { ...source, src, type })

    // Drive the stream adapter directly. Formerly this happened via the
    // sourcechange event forwarded by PluginManager to the stream plugins;
    // adapters are no longer plugins, so the engine calls them itself. The
    // adapter is resolved/reused by source type (A2) and rebuilds its library
    // instance inside onSourceChange. Native sources have no adapter. The sink
    // (PR2) is the only channel the adapter uses to drive the engine back.
    const sourceSink = createStreamSink(coordinator.getSnapshot().generation)

    // Seed the quality menu from provider metadata BEFORE the stream adapter
    // attaches. loadSource() clears the ladder; dash/shaka may emit [] while
    // their library is still null/attaching. Official YouTube toDash can take
    // seconds — without an early seed the 画质 popup only shows the chrome.
    const providerQualities = mapProviderQualities(source.qualities)
    if (providerQualities.length > 0) {
      // Progressive/native: single rung is the active quality.
      // Adaptive DASH: leave currentId null so ABR stays auto until the
      // adapter reports a real variant (adapter may overwrite this list).
      const seedCurrentId = type === 'native'
        ? (providerQualities[0]?.id ?? null)
        : null
      sourceSink.qualitiesResolved(providerQualities, seedCurrentId)
    }

    const streamAdapter = resolveStreamAdapter(source)
    streamAdapter?.onSourceChange(source, sourceSink)

    // Re-assert provider ladder after adapter onSourceChange. Some adapters
    // (dash.js before player exists) used to publish [] and wipe the seed.
    if (providerQualities.length > 0 && qualities.length === 0) {
      const seedCurrentId = type === 'native'
        ? (providerQualities[0]?.id ?? null)
        : null
      sourceSink.qualitiesResolved(providerQualities, seedCurrentId)
    }

    if (type === 'native') {
      videoElement.src = src
      videoElement.load()
    }

  }

  const loadSource = async (source: MediaSource) => {
    if (!source.src) {
      logger.warn('[PlayerEngine] No source URL provided')
      return null
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
    if (nextKey === currentSourceKey || nextKey === pendingSourceKey) return null

    const lifecycle = coordinator.getSnapshot()
    const loadIntent = lifecycle.phase === 'resolving'
      ? lifecycle.intent
      : (autoplay ? 'play' : 'pause')
    const operation = coordinator.beginLoading(nextKey, loadIntent)

    coordinator.updateMedia({ bufferedPercent: 0 })
    markSourceLoadingStarted()
    errorRecovery.clearWaitingRecovery()
    currentQualityLabel = null
    currentQualityId = null
    registeredQualityId = null
    retryCount = 0

    // Prefer immediate provider seed over a blank menu flash. Pending loads
    // (engine not inited / no <video> yet) must still show the ladder so the
    // 画质 chip is usable the moment the user opens the popup.
    const earlyProviderQualities = mapProviderQualities(resolvedSource.qualities)
    if (earlyProviderQualities.length > 0) {
      qualities = earlyProviderQualities
      errorRecovery.setRecoveryQualities(earlyProviderQualities)
      events.emit('qualitiesloaded', earlyProviderQualities)
      if (resolvedSource.type === 'native') {
        currentQualityId = earlyProviderQualities[0]?.id ?? null
        currentQualityLabel = earlyProviderQualities[0]?.label ?? null
        registeredQualityId = currentQualityId
        if (currentQualityLabel) {
          emitQualityChange(currentQualityLabel, currentQualityId, false)
        }
      } else {
        // Adaptive: leave id null so ABR is free; chip shows a concrete height
        // (provisional ~720p-class) until the adapter reports the active track.
        currentQualityId = null
        registeredQualityId = null
        const sorted = [...earlyProviderQualities].sort(
          (a, b) => Number(b.height || 0) - Number(a.height || 0)
            || Number(b.bitrate || 0) - Number(a.bitrate || 0),
        )
        const provisional = sorted.find((item) => Number(item.height || 0) > 0 && Number(item.height || 0) <= 720)
          || sorted.find((item) => Number(item.height || 0) > 0)
          || sorted[0]
        currentQualityLabel = provisional?.label
          || (provisional?.height ? `${provisional.height}p` : null)
        if (currentQualityLabel) {
          emitQualityChange(currentQualityLabel, null, true)
        }
      }
    } else {
      qualities = []
      events.emit('qualitiesloaded', [])
    }

    currentSource = resolvedSource
    currentSourceType = (resolvedSource.type === 'hls' || resolvedSource.type === 'dash' || resolvedSource.type === 'native')
      ? resolvedSource.type
      : null

    events.emit('sourcetypechange', currentSourceType)

    if (!inited || !videoElement) {
      pendingSource = resolvedSource
      pendingSourceKey = nextKey
    } else {
      doLoadSource(resolvedSource)
    }

    try {
      return await coordinator.waitFor(
        operation,
        state => (
          state.phase === 'ready'
          || state.phase === 'playing'
          || state.phase === 'paused'
          || state.phase === 'error'
        ),
        60_000,
      )
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return null
      const playerError: PlayerError = {
        code: 'LOAD_TIMEOUT',
        message: errorMessage(error, 'Playback source load timed out'),
        fatal: true,
      }
      coordinator.fail(playerError)
      return null
    }
  }

  let removeVideoListeners: (() => void) | null = null
  const setupVideoListeners = (): void => {
    if (!videoElement) return
    if (removeVideoListeners) return

    const video = videoElement

    const onPlay = () => {
      suppressMediaLifecycle = false
      suppressMediaPauseIntent = false
      coordinator.setIntent('play')
      errorRecovery.clearWaitingRecovery()
      events.emit('play', undefined)
      options.onPlay?.()
    }
    const onPause = () => {
      if (suppressMediaPauseIntent || suppressMediaLifecycle) return
      coordinator.markPaused()
      errorRecovery.clearWaitingRecovery()
      flushProgress()
      events.emit('pause', undefined)
      options.onPause?.()
    }
    const onEnded = () => {
      if (suppressMediaLifecycle) return
      coordinator.markEnded()
      errorRecovery.clearWaitingRecovery()
      flushProgress()
      events.emit('ended', undefined)
      options.onEnded?.()
    }
    const onTimeUpdate = () => {
      if (suppressMediaLifecycle) return
      const currentMediaTime = video.currentTime
      const playheadMoved = Number.isFinite(lastTimeUpdateMediaTime)
        && Math.abs(currentMediaTime - lastTimeUpdateMediaTime) >= 0.01
      lastTimeUpdateMediaTime = currentMediaTime
      coordinator.updateMedia({ currentTime: video.currentTime, duration: video.duration })
      // Post-seek safety net: if the playhead has media (or is actually moving),
      // never leave the UI spinner up even when buffering/canplay events miss.
      if (coordinator.getSnapshot().loading && pendingSeekOperationId === null) {
        if (
          hasMediaAhead(video)
          || (playheadMoved && !video.paused && video.playbackRate > 0 && video.readyState >= 2)
        ) {
          ensurePlaybackRate(video)
          clearLoadingState('timeupdate-ahead')
        }
      }
      scheduleProgressSave()
      events.emit('timeupdate', { currentTime: video.currentTime, duration: video.duration })
      options.onTimeUpdate?.(video.currentTime)
    }
    const onDurationChange = () => {
      if (suppressMediaLifecycle) return
      coordinator.updateMedia({ duration: video.duration })
      events.emit('durationchange', video.duration)
    }
    const onLoadStart = () => {
      suppressMediaLifecycle = false
      suppressMediaPauseIntent = false
      mediaLoadStartedForCurrentSource = true
      mediaMetadataLoadedForCurrentSource = false
      events.emit('loadsstart', undefined)
    }
    const onLoadedMetadata = () => {
      if (!isNativeMediaSourceCurrent()) return
      suppressMediaLifecycle = false
      suppressMediaPauseIntent = false
      mediaMetadataLoadedForCurrentSource = true
      coordinator.updateMedia({ duration: video.duration })
      events.emit('loadedmetadata', { duration: video.duration, videoWidth: video.videoWidth, videoHeight: video.videoHeight })
    }
    const onLoadedData = () => {
      if (suppressMediaLifecycle) return
      if (!isNativeMediaSourceCurrent()) return
      events.emit('loadeddata', undefined)
    }
    const onProgress = () => {
      if (suppressMediaLifecycle) return
      if (video.buffered.length > 0 && video.duration > 0) {
        const bufferedEnd = video.buffered.end(video.buffered.length - 1)
        coordinator.updateMedia({ bufferedPercent: (bufferedEnd / video.duration) * 100 })
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
      if (suppressMediaLifecycle) return
      // DASH buffering is owned by the stream adapter. Native waiting still
      // fires on MSE gap seeks and would fight Shaka's buffering=false by
      // re-arming the stall timer while rate is still 0 — leave it to the adapter.
      if (streamAdapterOwnsBuffering()) return
      coordinator.markBuffering()
      errorRecovery.scheduleWaitingRecovery()
      events.emit('waiting', undefined)
    }
    const onStalled = () => {
      if (suppressMediaLifecycle) return
      if (streamAdapterOwnsBuffering()) return
      coordinator.markBuffering()
      events.emit('waiting', undefined)
    }
    const onSeeked = () => {
      if (pendingSeekOperationId !== null) {
        events.emit('seeked', video.currentTime)
        return
      }
      if (suppressMediaLifecycle) return
      // After scrub settles: FreeTube drops the loading symbol when Shaka is no
      // longer buffering. We approximate with range coverage OR a playable
      // readyState at the new playhead (range is authoritative when present).
      if (coordinator.getSnapshot().loading && (hasMediaAhead(video) || video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA)) {
        if (video.playbackRate === 0) ensurePlaybackRate(video)
        // readyState alone can be stale — only clear on readyState if the
        // playhead is inside a buffered range OR stream adapter will re-assert.
        if (hasMediaAhead(video) || currentSourceType === 'native') {
          clearLoadingState('seeked-ahead')
          if (coordinator.getSnapshot().intent === 'play') {
            void play().catch((e) => {
              logger.warn('[PlayerEngine] Play after seeked-ahead failed', e)
            })
          }
        }
      }
      events.emit('seeked', video.currentTime)
    }
    const onPlaying = () => {
      suppressMediaLifecycle = false
      // Playback resumed — clear spinner even if Shaka never re-fired
      // buffering=false (FakeEvent prop miss / race with our seek waiting).
      // Also undo a stuck rate=0 so "playing" is not a silent freeze.
      if (video.playbackRate === 0) ensurePlaybackRate(video)
      if (pendingSeekOperationId !== null) {
        events.emit('playing', undefined)
        return
      }
      clearLoadingState('playing')
      coordinator.markPlaying()
      events.emit('playing', undefined)
    }
    const onCanPlay = () => {
      if (suppressMediaLifecycle) return
      if (!canAcceptNativeCanPlay()) return
      clearLoadingState('native-canplay')

      if (coordinator.getSnapshot().intent === 'play') {
        void play().catch((e) => {
          logger.warn('[PlayerEngine] Auto-play failed after canplay', e)
        })
      }
    }
    const onError = (e: Event) => {
      if (suppressMediaLifecycle || coordinator.getSnapshot().phase === 'resolving') return
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
      void recoverFromError(err, 'Native media')
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
    video.addEventListener('seeked', onSeeked)
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
      video.removeEventListener('seeked', onSeeked)
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
    if (currentStreamAdapter) {
      currentStreamAdapter.destroy()
      currentStreamAdapter = null
      currentAdapterType = null
    }
    pluginManager.destroy()
    suppressMediaPauseIntent = true
    releaseVideoElementMedia(videoElement)
    removeCoordinatorListener()
    if (ownsCoordinator) coordinator.destroy()
    events.destroy()
  }

  const attachVideoElement = (el: HTMLVideoElement | null): void => {
    if (videoElement === el) return
    const previousVideoElement = videoElement

    if (removeVideoListeners) {
      removeVideoListeners()
    }

    errorRecovery.clearWaitingRecovery()
    lastTimeUpdateMediaTime = Number.NaN
    suppressMediaPauseIntent = true
    suppressMediaLifecycle = true
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

  /**
   * Shaka sets playbackRate=0 while buffering (STARVING). If that flag sticks
   * after rebuffer, play() succeeds but A/V never advance — classic post-scrub
   * freeze. Always restore the engine's intended rate before play().
   */
  const ensurePlaybackRate = (el: HTMLVideoElement): void => {
    const intended = Number.isFinite(playbackRate) && playbackRate > 0 ? playbackRate : 1
    if (el.playbackRate === 0 || !Number.isFinite(el.playbackRate) || el.playbackRate < 0) {
      try {
        el.playbackRate = intended
        el.defaultPlaybackRate = intended
      } catch (e) {
        logger.warn('[PlayerEngine] Failed to restore playbackRate', e)
      }
    }
  }

  const play = async (): Promise<boolean> => {
    coordinator.setIntent('play')
    // During provider resolution the attached element still belongs to the
    // detached previous source. Queue intent without touching or reviving it.
    if (coordinator.getSnapshot().phase === 'resolving') return true
    if (!videoElement) return false
    try {
      if (audioContext?.state === 'suspended') {
        await audioContext.resume()
      }
      ensurePlaybackRate(videoElement)
      await videoElement.play()
      // play() can leave rate 0 if Shaka re-entered STARVING mid-call; re-check.
      ensurePlaybackRate(videoElement)
      return true
    } catch (e) {
      logger.warn('[PlayerEngine] Play failed', e)
      return false
    }
  }

  const pause = (): void => {
    coordinator.setIntent('pause')
    if (coordinator.getSnapshot().phase === 'resolving') {
      suspendForSourceChange()
      return
    }
    if (!videoElement) return
    videoElement.pause()
  }

  const suspendForSourceChange = (): void => {
    suppressMediaPauseIntent = true
    suppressMediaLifecycle = true
    videoElement?.pause()
  }

  const seek = async (time: number) => {
    if (!videoElement) return null
    // A seek against the detached previous element must never supersede the
    // active provider resolve operation for the next video.
    if (coordinator.getSnapshot().phase === 'resolving') return null
    errorRecovery.clearWaitingRecovery()
    // Allow googlevideo segment fetch after scrub, but do not suppress so long
    // that a stuck rebuffer is invisible — soft recovery uses retryStreaming
    // (not re-seek) so a few seconds is enough.
    errorRecovery.suppressWaitingRecovery(Math.max(retryDelay * 2, 4000))
    const target = Number(time)
    if (!Number.isFinite(target)) return null
    const clamped = Math.max(0, target)
    // If the user was watching (or element is "playing" at rate 0 while Shaka
    // buffers), re-arm play once the stream adapter reports not buffering.
    // rate===0 is never a user pause — treat it as still wanting playback.
    const operation = coordinator.beginSeek(
      clamped,
      coordinator.getSnapshot().intent === 'play',
    )
    pendingSeekOperationId = operation.operationId
    // A timeupdate caused only by assigning currentTime is not proof that
    // playback resumed; movement must occur beyond this landing point.
    lastTimeUpdateMediaTime = clamped

    // FreeTube does NOT force a loading overlay on every seek — spinner tracks
    // shaka Player "buffering". Forcing waiting=true here was the main reason
    // scrub left a permanent spinner: if Shaka never re-emitted buffering=false
    // (or only buffered ~0.02s), our old 0.5s probe never cleared store.loading.
    const streamOwned = streamAdapterOwnsBuffering()

    let driverCompletion: Promise<StreamSeekResult | void> = Promise.resolve()
    try {
      // Prefer the stream adapter's seek when available so dash.js rebuffers
      // at the target without resetting the MediaSource attachment.
      if (currentStreamAdapter?.seek) {
        driverCompletion = Promise.resolve(currentStreamAdapter.seek(clamped))
      } else {
        videoElement.currentTime = clamped
      }
    } catch (e) {
      logger.warn('[PlayerEngine] Seek failed', e)
      if (pendingSeekOperationId === operation.operationId) pendingSeekOperationId = null
      coordinator.markReady(Boolean(!videoElement.paused && !videoElement.ended))
      return null
    }

    // Already-buffered landings: clear immediately (tiny ahead is enough).
    if (hasMediaAhead(videoElement) && !currentStreamAdapter?.seek) {
      ensurePlaybackRate(videoElement)
      if (coordinator.getSnapshot().loading) clearLoadingState('seek-ahead')
      if (coordinator.getSnapshot().intent === 'play') {
        void play().catch((e) => {
          logger.warn('[PlayerEngine] Play after buffered seek failed', e)
        })
      }
    } else if (streamOwned) {
      // Unbuffered DASH seek: show spinner; adapter buffering=false +
      // adapter loadingStateChanged(false) is the primary clear path.
      // Adapter seek() also re-syncs isBuffering() on a microtask.
      events.emit('waiting', undefined)
      errorRecovery.scheduleWaitingRecovery()
    } else {
      events.emit('waiting', undefined)
      errorRecovery.scheduleWaitingRecovery()
    }
    events.emit('seeking', clamped)

    try {
      const driverResult = await driverCompletion
      if (!coordinator.isCurrent(operation)) return null
      if (pendingSeekOperationId === operation.operationId) pendingSeekOperationId = null

      // Adapters such as Shaka resolve seek() only after a destination frame
      // was presented (including decoder/manifest repair when necessary).
      // Void adapters fall through immediately and remain event-driven when
      // their destination is not buffered yet.
      if (driverResult?.visuallyReady || (driverResult === undefined && hasMediaAhead(videoElement))) {
        ensurePlaybackRate(videoElement)
        coordinator.markReady(!videoElement.paused && !videoElement.ended)
        if (coordinator.getSnapshot().intent === 'play') {
          void play().catch((e) => {
            logger.warn('[PlayerEngine] Play after visually completed seek failed', e)
          })
        }
      }

      return await coordinator.waitFor(
        operation,
        state => (
          state.phase === 'ready'
          || state.phase === 'playing'
          || state.phase === 'paused'
          || state.phase === 'error'
        ),
        20_000,
      )
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        logger.warn('[PlayerEngine] Seek operation did not settle', error)
        if (coordinator.isCurrent(operation)) {
          await recoverFromError({
            code: 'SEEK_TIMEOUT',
            message: errorMessage(error, 'Playback seek timed out'),
            fatal: false,
          }, 'Seek timeout')
        }
      }
      return null
    } finally {
      if (pendingSeekOperationId === operation.operationId) pendingSeekOperationId = null
    }
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

    // Stream adapter drives quality directly (formerly a name-keyed
    // pluginManager.get<QualityController> dispatch duplicated in three places;
    // see docs/adr/0001). The adapter is already resolved for the current
    // source; native sources have no adapter and no quality control.
    currentStreamAdapter?.setQuality(controllerQuality)

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

  const getSubtitleStyle = (): SubtitleStyle => {
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

  const setSubtitleStyle = (style: SubtitleStyle): void => {
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
      bufferedPercent: coordinator.getSnapshot().bufferedPercent,
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
    suspendForSourceChange,
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
    getState,
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
    getStreamAdapter: () => currentStreamAdapter,
    getStats,
    on: events.on.bind(events),
    off: events.off.bind(events)
  }
}

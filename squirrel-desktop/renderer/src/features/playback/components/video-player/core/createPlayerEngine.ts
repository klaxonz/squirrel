/**
 * Player engine factory.
 *
 * ponytail: this file is intentionally a single cohesive module (~900 lines of
 * logic) rather than split into per-feature sub-modules. The engine is a state
 * machine: ~30 closure variables (video element, audio graph, source/quality/
 * subtitle/progress state) are read and written by overlapping subsets of the
 * play/pause/seek/volume/quality/subtitle/source/progress operations. Splitting
 * would force a state-object + getter/setter seam (the cost is visible in
 * error-recovery.ts, which already needs ~28 deps for its narrower concern) for
 * every cross-cutting read — a net readability loss.
 *
 * The genuinely isolatable concerns ARE split out: error recovery lives in
 * error-recovery.ts, public types in engine-types.ts, plugin management in
 * PluginManager.ts, events in EventEmitter.ts. What remains here is the core
 * playback state machine, which is most readable as one file.
 */

import { EventEmitter } from './EventEmitter'
import { PluginManager } from './PluginManager'
import { LocalStorageAdapter, type UserConfig, type PlaybackProgress } from './PlayerAdapter'
import { playerLogger } from './logger'
import { createErrorRecovery, MAX_VOLUME, detectSourceType } from './error-recovery'
import type { StreamAdapter, StreamAdapterType, StreamContext } from './StreamAdapter'
import type { StreamSink } from './StreamSink'
import { HlsAdapter } from '../adapters/HlsAdapter'
import { DashAdapter } from '../adapters/DashAdapter'
import { ShakaDashAdapter } from '../adapters/ShakaDashAdapter'
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

  // Stream adapter seam (see docs/adr/0001). The engine owns one adapter at a
  // time, keyed by currentAdapterType; loadSource reuses it when the source
  // type is unchanged and destroys + rebuilding it otherwise (A2 strategy).
  let currentStreamAdapter: StreamAdapter | null = null
  let currentAdapterType: StreamAdapterType | null = null
  // The engine's StreamSink (PR2): the only channel adapters use to drive the
  // engine. Lazily created; stable for the engine's lifetime.
  let streamSink: StreamSink | null = null

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
  getStreamAdapter: () => currentStreamAdapter,
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

  const createStreamSink = (): StreamSink => ({
    qualitiesResolved: (qs, currentId) => {
      publishQualities(Array.isArray(qs) ? qs : [], currentId)
    },

    qualityChanged: (quality) => {
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
      if (isLoading) {
        loading = true
        errorRecovery.scheduleWaitingRecovery()
      } else {
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
    },

    error: (error) => {
      pluginHandlingError = true
      void errorRecovery.handleRecoveryError(error)
        .then((recovered) => {
          if (!recovered) errorRecovery.reportFatalError(error)
          pluginHandlingError = false
        })
        .catch((e) => {
          logger.warn('[PlayerEngine] Stream adapter recovery chain failed', e)
          errorRecovery.reportFatalError(error)
          pluginHandlingError = false
        })
    },
  })

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

    markSourceLoadingStarted()
    pluginHandlingError = false

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
    if (!streamSink) streamSink = createStreamSink()

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
      streamSink.qualitiesResolved(providerQualities, seedCurrentId)
    }

    const streamAdapter = resolveStreamAdapter(source)
    streamAdapter?.onSourceChange(source, streamSink)

    // Re-assert provider ladder after adapter onSourceChange. Some adapters
    // (dash.js before player exists) used to publish [] and wipe the seed.
    if (providerQualities.length > 0 && qualities.length === 0) {
      const seedCurrentId = type === 'native'
        ? (providerQualities[0]?.id ?? null)
        : null
      streamSink.qualitiesResolved(providerQualities, seedCurrentId)
    }

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
    const onSeeked = () => {
      // After scrub settles, drop the spinner as soon as we have media ahead.
      // Waiting for a late canplay after DASH index seeks left users spinning
      // even when the playhead was already buffered.
      try {
        if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
          loading = false
          errorRecovery.clearWaitingRecovery()
        } else {
          const t = video.currentTime
          const { buffered } = video
          for (let i = 0; i < buffered.length; i += 1) {
            if (buffered.start(i) <= t + 0.35 && buffered.end(i) >= t + 0.5) {
              loading = false
              errorRecovery.clearWaitingRecovery()
              break
            }
          }
        }
      } catch {
        // ignore buffer probe failures
      }
      events.emit('seeked', video.currentTime)
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
    // Keep stall recovery suppressed long enough for DASH index + googlevideo
    // segment fetch after a seek lands. Live scrub no longer multi-fires seek.
    errorRecovery.suppressWaitingRecovery(Math.max(retryDelay * 4, 12000))
    const target = Number(time)
    if (!Number.isFinite(target)) return
    const clamped = Math.max(0, target)
    loading = true
    try {
      // Prefer the stream adapter's seek when available so dash.js rebuffers
      // at the target without resetting the MediaSource attachment.
      if (currentStreamAdapter?.seek) {
        currentStreamAdapter.seek(clamped)
      } else {
        videoElement.currentTime = clamped
      }
    } catch (e) {
      logger.warn('[PlayerEngine] Seek failed', e)
      loading = false
      return
    }
    errorRecovery.scheduleWaitingRecovery()
    events.emit('seeking', clamped)
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
    getStreamAdapter: () => currentStreamAdapter,
    getStats,
    on: events.on.bind(events),
    off: events.off.bind(events)
  }
}

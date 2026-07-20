import { EventEmitter } from './EventEmitter'
import type { StreamAdapter } from './StreamAdapter'
import type { IPlayerAdapter } from './PlayerAdapter'
import type {
  MediaSource,
  PlayerError,
  PlayerEvents,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext,
  QualityLevel,
} from './types'
import { type PlayerLogger } from './logger'

export const MAX_VOLUME = 200

export const detectSourceType = (src: string): 'hls' | 'dash' | 'native' => {
  const url = src.toLowerCase()
  if (url.includes('.m3u8') || url.includes('format=m3u8')) return 'hls'
  // FreeTube YouTube MPD is a data:application/dash+xml URL (no .mpd suffix).
  // Blob object URLs from createObjectURL are opaque — callers must set
  // type:'dash' explicitly (Bilibili does). YouTube uses data: and is covered.
  if (
    url.includes('.mpd')
    || url.includes('/mpd')
    || url.includes('format=mpd')
    || url.startsWith('data:application/dash+xml')
  ) {
    return 'dash'
  }
  return 'native'
}

export interface ErrorRecoveryDeps {
  getVideoElement: () => HTMLVideoElement | null
  getLoading: () => boolean
  setLoading: (v: boolean) => void
  getRetryCount: () => number
  setRetryCount: (v: number) => void
  getQualities: () => QualityLevel[]
  setQualities: (qs: QualityLevel[]) => void
  getRegisteredQualityId: () => string | number | null
  getCurrentSource: () => MediaSource | null
  getCurrentSourceType: () => 'native' | 'hls' | 'dash' | null
  getCurrentSourceKey: () => string
  setCurrentSourceKey: (k: string) => void
  getPendingSourceKey: () => string
  setPendingSourceKey: (k: string) => void
  getAutoPlayOnReady: () => boolean
  setAutoPlayOnReady: (v: boolean) => void
  getProgressKey: () => string | null
  getMaxRetries: () => number
  getRetryDelay: () => number
  getEnableQualityFallback: () => boolean
  events: EventEmitter<PlayerEvents>
  getStreamAdapter: () => StreamAdapter | null
  logger: PlayerLogger
  adapter: IPlayerAdapter
  onError?: (error: PlayerError) => void
  play: () => Promise<boolean>
  setQuality: (q: string | number) => void
  doLoadSource: (source: MediaSource) => void
}

export function createErrorRecovery(deps: ErrorRecoveryDeps) {
  let isRecovering = false
  let waitingRecoveryTimer: ReturnType<typeof setTimeout> | null = null
  let waitingRecoverySuppressedUntil = 0

  const clearWaitingRecovery = (): void => {
    if (!waitingRecoveryTimer) return
    clearTimeout(waitingRecoveryTimer)
    waitingRecoveryTimer = null
  }

  const hasBufferAhead = (video: HTMLVideoElement, minAheadSec = 0.75): boolean => {
    try {
      const t = video.currentTime
      const { buffered } = video
      for (let i = 0; i < buffered.length; i += 1) {
        if (buffered.start(i) <= t + 0.35 && buffered.end(i) >= t + minAheadSec) {
          return true
        }
      }
    } catch {
      // ignore
    }
    return false
  }

  const scheduleWaitingRecovery = (): void => {
    clearWaitingRecovery()
    const videoElement = deps.getVideoElement()
    const stalledAtTime = videoElement?.currentTime ?? 0
    const suppressionDelay = Math.max(0, waitingRecoverySuppressedUntil - Date.now())
    // Seek/buffer recovery needs a longer fuse than ordinary mid-play stalls —
    // DASH index seeks against googlevideo often take >5s without being dead.
    waitingRecoveryTimer = setTimeout(() => {
      waitingRecoveryTimer = null
      if (!videoElement || !deps.getLoading() || videoElement.ended) return
      if (Math.abs((videoElement.currentTime ?? 0) - stalledAtTime) > 1) return
      // Already have media queued ahead — drop the spinner, no recovery.
      if (hasBufferAhead(videoElement)) {
        deps.setLoading(false)
        return
      }

      const err: PlayerError = {
        code: 'STALL_DETECTED',
        message: 'Playback stalled while waiting for media',
        fatal: false,
      }
      void handleRecoveryError(err)
        .then((recovered) => {
          if (!recovered) reportFatalError(err)
        })
        .catch((e) => {
          deps.logger.warn('[ErrorRecovery] Recovery chain failed', e)
          reportFatalError(err)
        })
    }, Math.max(deps.getRetryDelay() * 3, 8000) + suppressionDelay)
  }

  const reportFatalError = (error: PlayerError): void => {
    deps.setLoading(false)
    deps.events.emit('error', error)
    deps.onError?.(error)
    const currentSource = deps.getCurrentSource()
    void deps.adapter.reportError({
      sourceUrl: currentSource?.src,
      errorCode: error.code,
      errorMessage: error.message,
      progressKey: deps.getProgressKey() ?? undefined,
      timestamp: Date.now(),
    }).catch((e) => {
      deps.logger.warn('[ErrorRecovery] Report error failed', e)
    })
  }

  const setRecoveryQualities = (qs: QualityLevel[]): void => {
    deps.setQualities(qs)
    deps.setRetryCount(0)
  }

  const getNextLowerQuality = (): QualityLevel | null => {
    const sorted = [...deps.getQualities()].sort((a, b) => (b.height || 0) - (a.height || 0))
    const currentId = deps.getRegisteredQualityId()
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
    const retryCount = deps.getRetryCount()
    const maxRetries = deps.getMaxRetries()
    const enableQualityFallback = deps.getEnableQualityFallback()
    const canFallbackQuality = enableQualityFallback && !!getNextLowerQuality()

    if (code.includes('NOT_SUPPORTED') || code.includes('CAPABILITY')) {
      // MEDIA_NOT_SUPPORTED is often a 403/expired CDN body, not a real codec
      // capability miss — allow retry/fallback below for those codes only.
      if (!code.includes('MEDIA_NOT_SUPPORTED') && !code.includes('SRC_NOT_SUPPORTED')) {
        return 'none'
      }
    }

    // Mid-playback / post-seek buffer stalls: soft retry first (adapter must
    // NOT reload the whole source — that resets the playhead). Only step down
    // quality after soft retries are exhausted.
    if (code.includes('STALL') || code.includes('BUFFER')) {
      if (retryCount < maxRetries) return 'retry'
      if (canFallbackQuality) return 'quality-fallback'
      return 'none'
    }

    if (code.includes('NETWORK') || code.includes('TIMEOUT') || code.includes('MEDIA_NOT_SUPPORTED') || code.includes('SRC_NOT_SUPPORTED')) {
      if (retryCount < maxRetries) return 'retry'
      if (canFallbackQuality) return 'quality-fallback'
    }

    if (code.includes('MEDIA') || code.includes('DECODE')) {
      if (canFallbackQuality) return 'quality-fallback'
      if (retryCount < maxRetries) return 'retry'
    }

    if (!error.fatal && retryCount < maxRetries) return 'retry'
    if (error.fatal && retryCount < maxRetries) return 'retry'
    return 'none'
  }

  const executeQualityFallback = (): boolean => {
    const nextQuality = getNextLowerQuality()
    if (!nextQuality) return false

    deps.logger.debug(`[ErrorRecovery] Falling back to quality: ${nextQuality.label}`)
    deps.setRetryCount(0)
    deps.setLoading(true)
    // Give the new representation time to buffer before the next stall timer fires.
    suppressWaitingRecovery(Math.max(deps.getRetryDelay() * 2, 4000))
    deps.setQuality(nextQuality.id ?? nextQuality.label)
    // Re-arm stall detection after the suppression window so a still-broken
    // stream can step down again instead of hanging forever on the spinner.
    scheduleWaitingRecovery()
    return true
  }

  const getStreamController = (): StreamAdapter | null => {
    return deps.getStreamAdapter()
  }

  const buildRecoveryContext = (): PlaybackRecoveryContext => ({
    retryCount: deps.getRetryCount(),
    maxRetries: deps.getMaxRetries(),
    retryDelay: deps.getRetryDelay(),
    source: deps.getCurrentSource() ? { ...deps.getCurrentSource()! } : null,
    currentTime: deps.getVideoElement()?.currentTime ?? 0,
    wasPlaying: !!deps.getVideoElement() && !deps.getVideoElement()!.paused && !deps.getVideoElement()!.ended
  })

  const reloadCurrentSource = (): boolean => {
    const currentSource = deps.getCurrentSource()
    if (!currentSource) return false

    const retryCount = deps.getRetryCount()
    const maxRetries = deps.getMaxRetries()
    const videoElement = deps.getVideoElement()

    const altSources = currentSource.alternativeSources || []
    if (altSources.length > 0 && retryCount >= maxRetries) {
      const altIndex = (retryCount - maxRetries) % altSources.length
      const alt = altSources[altIndex]
      if (alt && alt.src) {
        deps.logger.debug(`[ErrorRecovery] Switching to alternative source type=${alt.type}: ${alt.src}`)
        const altSource: MediaSource = {
          ...currentSource,
          src: alt.src,
          type: alt.type,
        }
        deps.setCurrentSourceKey('')
        deps.setPendingSourceKey('')
        deps.doLoadSource(altSource)
        return true
      }
    }

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
          deps.logger.warn('[ErrorRecovery] Failed to restore playback position after reload', error)
        }
      }, { once: true })
    }

    deps.setCurrentSourceKey('')
    deps.setPendingSourceKey('')
    deps.doLoadSource(sourceToReload)

    if (shouldResumePlayback) {
      deps.setAutoPlayOnReady(true)
    }

    deps.logger.debug('[ErrorRecovery] Reloaded current source')
    return true
  }

  const executeRetry = async (error: PlayerError): Promise<boolean> => {
    deps.setRetryCount(deps.getRetryCount() + 1)
    deps.logger.debug(`[ErrorRecovery] Retry attempt ${deps.getRetryCount()}/${deps.getMaxRetries()}`)
    await new Promise((resolve) => setTimeout(resolve, deps.getRetryDelay()))

    const code = String(error.code || '')
    const isStall = code.includes('STALL') || code.includes('BUFFER')
    const controller = getStreamController()
    const recoveryAction: PlaybackRecoveryAction = controller
      ? await controller.recoverPlayback(error, {
          ...buildRecoveryContext(),
          retryCount: deps.getRetryCount(),
        })
      : (isStall ? 'handled' : 'reload-source')

    if (recoveryAction === 'handled') {
      // Soft recovery does not clear loading by itself; re-arm the stall timer
      // so we can step down quality later if the buffer never refills.
      if (isStall && deps.getLoading()) {
        suppressWaitingRecovery(Math.max(deps.getRetryDelay(), 2000))
        scheduleWaitingRecovery()
      }
      return true
    }

    // Never full-reload on pure stalls — that rewinds the playhead to 0.
    if (recoveryAction === 'reload-source' && !isStall) {
      return reloadCurrentSource()
    }

    if (recoveryAction === 'reload-source' && isStall) {
      deps.logger.debug('[ErrorRecovery] Ignoring reload-source for stall to preserve seek position')
      if (deps.getLoading()) {
        suppressWaitingRecovery(Math.max(deps.getRetryDelay(), 2000))
        scheduleWaitingRecovery()
      }
      return true
    }

    return false
  }

  const handleRecoveryError = async (error: PlayerError): Promise<boolean> => {
    if (isRecovering) {
      // Another recovery is in flight — do NOT report fatal for the duplicate.
      deps.logger.debug('[ErrorRecovery] Already recovering, suppressing duplicate')
      return true
    }

    const code = String(error.code || '')
    if (code.includes('STALL')) {
      const videoElement = deps.getVideoElement()
      // Paused mid-buffer (autoplay policy / accidental pause): just resume.
      if (videoElement && !videoElement.ended && videoElement.paused) {
        try {
          const played = await deps.play()
          if (played !== false) {
            deps.logger.debug('[ErrorRecovery] Recovered stall via play()')
            return true
          }
        } catch (e) {
          deps.logger.warn('[ErrorRecovery] Stall play() failed', e)
        }
      }
      // Mid-playback stall while not paused: fall through to quality/retry.
      // The previous early `return false` turned every 5s buffer stall into a
      // fatal "播放出错 / 缓冲中" overlay even when lower qualities remained.
    }

    isRecovering = true
    try {
      const strategy = determineRecoveryStrategy(error)
      deps.logger.debug(`[ErrorRecovery] Strategy: ${strategy}, Error`, error)

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

  const suppressWaitingRecovery = (duration: number): void => {
    waitingRecoverySuppressedUntil = Date.now() + duration
  }

  // ponytail: the returned object only exposes what the engine actually
  // calls. Internal helpers (determineRecoveryStrategy, executeRetry,
  // executeQualityFallback, getNextLowerQuality, getStreamController,
  // buildRecoveryContext, reloadCurrentSource) stay closure-local; leaking
  // them onto the return object created a false public API.
  return {
    clearWaitingRecovery,
    scheduleWaitingRecovery,
    handleRecoveryError,
    reportFatalError,
    setRecoveryQualities,
    suppressWaitingRecovery,
  }
}

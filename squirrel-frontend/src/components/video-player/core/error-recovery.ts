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
  if (url.includes('.mpd') || url.includes('/mpd') || url.includes('format=mpd')) return 'dash'
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

  const scheduleWaitingRecovery = (): void => {
    clearWaitingRecovery()
    const videoElement = deps.getVideoElement()
    const stalledAtTime = videoElement?.currentTime ?? 0
    const suppressionDelay = Math.max(0, waitingRecoverySuppressedUntil - Date.now())
    waitingRecoveryTimer = setTimeout(() => {
      waitingRecoveryTimer = null
      if (!videoElement || !deps.getLoading() || videoElement.ended) return
      if (Math.abs((videoElement.currentTime ?? 0) - stalledAtTime) > 1) return

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
    }, Math.max(deps.getRetryDelay() * 2, 5000) + suppressionDelay)
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

    deps.logger.debug(`[ErrorRecovery] Falling back to quality: ${nextQuality.label}`)
    deps.setRetryCount(0)
    deps.setQuality(nextQuality.id ?? nextQuality.label)
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

    const controller = getStreamController()
    const recoveryAction: PlaybackRecoveryAction = controller
      ? await controller.recoverPlayback(error, {
          ...buildRecoveryContext(),
          retryCount: deps.getRetryCount()
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
      deps.logger.debug('[ErrorRecovery] Already recovering, skipping')
      return false
    }

    const code = String(error.code || '')
    if (code.includes('STALL')) {
      const videoElement = deps.getVideoElement()
      if (videoElement && !videoElement.ended && videoElement.paused) {
        try {
          await videoElement.play()
          deps.logger.debug('[ErrorRecovery] Recovered stall via play()')
          return true
        } catch (e) {
          deps.logger.warn('[ErrorRecovery] Stall play() failed', e)
        }
      }
      return false
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

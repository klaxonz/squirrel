import { ref, watch, type ComputedRef, type Ref } from 'vue'
import type { MediaSource } from '../core'

export interface UseSourceSyncOptions {
  /** The raw <video> element ref (read for readyState / addEventListener). */
  videoRef: Ref<HTMLVideoElement | null>
  /** Reactive props the source-sync reads. */
  source: Ref<MediaSource | null | undefined>
  initialTime: Ref<number | undefined>
  autoplay: ComputedRef<boolean> | Ref<boolean> | boolean
  /** Player-derived reactive state. */
  currentTime: Ref<number>
  isPlaying: ComputedRef<boolean> | Ref<boolean>
  hasStartedPlayback: ComputedRef<boolean> | Ref<boolean> | boolean
  /** Transport actions. */
  loadSource: (source: MediaSource) => void
  play: () => unknown
  pause: () => void
  seek: (time: number) => void
  /** Called when a new source is detected so the caller can clear its UI. */
  onSourceChange: () => void
}

export interface UseSourceSyncReturn {
  /** Clear the source-swap listeners + reset bookkeeping (for onUnmounted). */
  cleanup: () => void
}

const getSourceIdentity = (source: MediaSource | null | undefined): string => {
  if (!source) return ''
  return String(source.key || source.src || '')
}

const autoplayValue = (a: UseSourceSyncOptions['autoplay']): boolean =>
  typeof a === 'boolean' ? a : a.value
const hasStartedValue = (h: UseSourceSyncOptions['hasStartedPlayback']): boolean =>
  typeof h === 'boolean' ? h : h.value

/**
 * Synchronizes the player engine with the `source` / `initialTime` props:
 *
 * - applies `initialTime` once per source (waits for metadata if needed),
 * - pauses + arms resume-after-swap when the source briefly goes null (e.g. the
 *   parent is swapping adapters) and resumes once the new source is ready,
 * - notifies the caller (`onSourceChange`) when the source identity changes so
 *   it can clear source-scoped UI (error overlay, etc.).
 *
 * Element listeners attached while waiting for `loadedmetadata` / `canplay` are
 * tracked and removed via `cleanup()` / on the next source change.
 */
export function useSourceSync(options: UseSourceSyncOptions): UseSourceSyncReturn {
  const {
    videoRef, source, initialTime, autoplay,
    currentTime, isPlaying, hasStartedPlayback,
    loadSource, play, pause, seek, onSourceChange,
  } = options

  const shouldResumeAfterSourceSwap = ref(false)
  let removeInitialTimeListener: (() => void) | null = null
  let removeResumeAfterSourceSwapListener: (() => void) | null = null
  let initialTimeAppliedSourceKey: string | null = null

  const clearInitialTimeListener = (): void => {
    if (!removeInitialTimeListener) return
    removeInitialTimeListener()
    removeInitialTimeListener = null
  }

  const clearResumeAfterSourceSwapListener = (): void => {
    if (!removeResumeAfterSourceSwapListener) return
    removeResumeAfterSourceSwapListener()
    removeResumeAfterSourceSwapListener = null
  }

  const applyInitialTime = (src: MediaSource | null | undefined, time: number | undefined): void => {
    const sourceKey = getSourceIdentity(src)
    if (!sourceKey || initialTimeAppliedSourceKey === sourceKey) return
    if (hasStartedValue(hasStartedPlayback) || currentTime.value > 0.5) return

    const video = videoRef.value
    const nextTime = Number(time)
    if (!video || !Number.isFinite(nextTime) || nextTime <= 0) return

    clearInitialTimeListener()

    const applySeek = (): void => {
      const durationValue = Number(video.duration)
      const boundedTime = Number.isFinite(durationValue) && durationValue > 0
        ? Math.min(nextTime, durationValue)
        : nextTime

      if (boundedTime <= 0) return
      initialTimeAppliedSourceKey = sourceKey
      seek(Math.max(0, boundedTime))
    }

    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      applySeek()
      return
    }

    const onLoadedMetadata = (): void => {
      clearInitialTimeListener()
      applySeek()
    }

    video.addEventListener('loadedmetadata', onLoadedMetadata, { once: true })
    removeInitialTimeListener = () => {
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
    }
  }

  const resumePlaybackAfterSourceSwap = (): void => {
    if (!shouldResumeAfterSourceSwap.value) return

    const video = videoRef.value
    if (!video) {
      shouldResumeAfterSourceSwap.value = false
      return
    }

    const resume = (): void => {
      clearResumeAfterSourceSwapListener()
      if (!shouldResumeAfterSourceSwap.value) return
      shouldResumeAfterSourceSwap.value = false
      void play()
    }

    if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
      resume()
      return
    }

    clearResumeAfterSourceSwapListener()
    video.addEventListener('canplay', resume, { once: true })
    removeResumeAfterSourceSwapListener = () => {
      video.removeEventListener('canplay', resume)
    }
  }

  watch(source, (s, previousSource) => {
    const sourceChanged = getSourceIdentity(s) !== getSourceIdentity(previousSource)
    if (sourceChanged) {
      clearInitialTimeListener()
      clearResumeAfterSourceSwapListener()
      initialTimeAppliedSourceKey = null
      onSourceChange()
    }
    if (!s) {
      shouldResumeAfterSourceSwap.value = isPlaying.value
      clearResumeAfterSourceSwapListener()
      pause()
      return
    }
    loadSource(s)
    if (shouldResumeAfterSourceSwap.value) {
      if (autoplayValue(autoplay)) {
        shouldResumeAfterSourceSwap.value = false
      } else {
        resumePlaybackAfterSourceSwap()
      }
    }
    applyInitialTime(s, initialTime.value)
  }, { immediate: true })

  watch(initialTime, (time) => {
    applyInitialTime(source.value, time)
  })

  const cleanup = () => {
    clearInitialTimeListener()
    clearResumeAfterSourceSwapListener()
  }

  return { cleanup }
}

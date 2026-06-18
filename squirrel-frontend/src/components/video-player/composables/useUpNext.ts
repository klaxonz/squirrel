import { computed, ref, type ComputedRef, type Ref } from 'vue'

export interface PlaylistEntryLike {
  title?: string
}

export interface UseUpNextOptions {
  playlistEntries: ComputedRef<PlaylistEntryLike[]> | Ref<PlaylistEntryLike[]>
  playlistIndex: ComputedRef<number | null> | Ref<number | null>
  /** Fired when the user presses "start now" or the countdown hits 0. Caller emits `next`. */
  onNext: () => void
}

export interface UseUpNextReturn {
  showUpNext: Ref<boolean>
  upNextCountdown: Ref<number>
  nextEpisodeTitle: ComputedRef<string>
  /**
   * Called by the parent's currentTime watcher when remaining playback time
   * crosses the threshold. Owns the countdown timer + overlay state.
   * No-op when there is no next playlist entry or remaining is outside (0, 30].
   */
  maybeStart: (remainingSeconds: number) => void
  /** User pressed "start now": clears overlay + fires onNext. */
  startNow: () => void
  clear: () => void
}

export function useUpNext(options: UseUpNextOptions): UseUpNextReturn {
  const { playlistEntries, playlistIndex, onNext } = options

  const showUpNext = ref(false)
  const upNextCountdown = ref(5)

  let upNextTimer: ReturnType<typeof setInterval> | null = null

  const hasNextEntry = computed(() => {
    const entries = playlistEntries.value || []
    const nextIdx = (playlistIndex.value ?? -1) + 1
    return nextIdx >= 0 && nextIdx < entries.length
  })

  const nextEpisodeTitle = computed(() => {
    const entries = playlistEntries.value || []
    const nextIdx = (playlistIndex.value ?? -1) + 1
    if (nextIdx >= 0 && nextIdx < entries.length) {
      return entries[nextIdx].title || `Episode ${nextIdx + 1}`
    }
    return ''
  })

  const fireNext = () => {
    showUpNext.value = false
    if (upNextTimer) {
      clearInterval(upNextTimer)
      upNextTimer = null
    }
    onNext()
  }

  const startNow = fireNext

  const maybeStart = (remainingSeconds: number) => {
    if (!hasNextEntry.value) return
    if (remainingSeconds > 30 || remainingSeconds <= 0) return
    if (showUpNext.value) return
    showUpNext.value = true
    upNextCountdown.value = Math.min(5, Math.floor(remainingSeconds))
    upNextTimer = setInterval(() => {
      upNextCountdown.value--
      if (upNextCountdown.value <= 0) {
        fireNext()
      }
    }, 1000)
  }

  const clear = () => {
    showUpNext.value = false
    if (upNextTimer) {
      clearInterval(upNextTimer)
      upNextTimer = null
    }
  }

  return {
    showUpNext,
    upNextCountdown,
    nextEpisodeTitle,
    maybeStart,
    startNow,
    clear,
  }
}

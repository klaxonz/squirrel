import type { ComputedRef } from 'vue'
import type { PlayerRuntimeStore } from '../runtime/PlayerStore'

/**
 * Controls-auto-hide orchestration.
 *
 * Owns the 3s idle timer that hides the control bar during playback and the
 * contract for showing controls (which the template's pointer/click handlers
 * call). Extracted verbatim from VideoPlayer.vue — the only behaviour change
 * is that the timer + the `controlsVisible`/`clearPreview`/`closeMenus` side
 * effects now live behind this seam instead of as loose module-level consts.
 *
 * Why a composable: the original code interleaved the hide timer with
 * pointer-move, scrub, fullscreen and play/pause watchers. Centralising the
 * timer here lets those callers call `showControls()` / `syncHideTimer()` /
 * `clearHideTimer()` without each one reaching for a shared `let hideTimer`.
 */
export interface UseControlAutoHideOptions {
  store: PlayerRuntimeStore
  isPlaying: ComputedRef<boolean> | { value: boolean }
  isScrubbing: ComputedRef<boolean> | { value: boolean }
  clearPreview: () => void
  closeMenus: () => void
}

export interface UseControlAutoHideReturn {
  showControls: () => void
  hideControls: () => void
  syncHideTimer: () => void
  clearHideTimer: () => void
}

const AUTO_HIDE_DELAY_MS = 3000

export function useControlAutoHide(options: UseControlAutoHideOptions): UseControlAutoHideReturn {
  const { store, isPlaying, isScrubbing, clearPreview, closeMenus } = options

  let hideTimer: ReturnType<typeof setTimeout> | undefined

  const clearHideTimer = () => {
    if (hideTimer === undefined) return
    clearTimeout(hideTimer)
    hideTimer = undefined
  }

  const hideControls = () => {
    clearHideTimer()
    store.setControlsVisible(false)
    clearPreview()
    closeMenus()
  }

  const syncHideTimer = () => {
    clearHideTimer()
    if (store.controlsVisible && isPlaying.value && !isScrubbing.value) {
      hideTimer = setTimeout(() => hideControls(), AUTO_HIDE_DELAY_MS)
    }
  }

  const showControls = () => {
    store.setControlsVisible(true)
    syncHideTimer()
  }

  return {
    showControls,
    hideControls,
    syncHideTimer,
    clearHideTimer,
  }
}

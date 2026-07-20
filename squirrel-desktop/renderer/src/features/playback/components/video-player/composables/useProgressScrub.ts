import { ref, type ComputedRef, type Ref } from 'vue'

export interface UseProgressScrubOptions {
  duration: Ref<number>
  /**
   * Clip-marker pending segment end (writable). While scrubbing, we keep it in
   * sync with the pointer so a marker segment being authored follows the cursor.
   */
  pendingSegmentEndTime: Ref<number | null>
  hasPendingSegment: ComputedRef<boolean>
  /** Seek to a given time when the user drags outside an active marker segment. */
  seek: (time: number) => void
}

export interface UseProgressScrubReturn {
  progressAreaRef: Ref<HTMLElement | null>
  previewTime: Ref<number | null>
  previewPercent: Ref<number>
  isScrubbing: Ref<boolean>
  onProgressPointerDown: (e: PointerEvent) => void
  onProgressPointerMove: (e: PointerEvent) => void
  onProgressPointerUp: (e?: PointerEvent) => void
  onProgressPointerLeave: () => void
  clearPreview: () => void
  cleanup: () => void
}

/**
 * Owns the progress-rail pointer scrub: preview thumbnail/time during drag,
 * commit seek once on pointer-up, plus optional clip-marker segment-end sync.
 *
 * Live-seeking on every pointermove is intentionally avoided — DASH/HLS
 * cancel in-flight segments on each currentTime write, which leaves the
 * player spinning then rewinding after a drag. Preview is visual-only until
 * release (or a simple click: down+up without move still seeks once).
 */
export function useProgressScrub(options: UseProgressScrubOptions): UseProgressScrubReturn {
  const { duration, pendingSegmentEndTime, hasPendingSegment, seek } = options

  const progressAreaRef = ref<HTMLElement | null>(null)
  const previewTime = ref<number | null>(null)
  const previewPercent = ref(0)
  const isScrubbing = ref(false)
  let activeProgressPointerId: number | null = null

  const updateProgressPreview = (e: PointerEvent) => {
    const progressArea = progressAreaRef.value
    if (!progressArea) return

    const rect = progressArea.getBoundingClientRect()
    if (rect.width <= 0) return

    const p = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    previewPercent.value = p * 100
    previewTime.value = p * duration.value

    // Visual + marker preview only while dragging — never touch media time here.
    if (isScrubbing.value) {
      pendingSegmentEndTime.value = previewTime.value
    }
  }

  const commitScrubSeek = () => {
    if (previewTime.value === null || !Number.isFinite(previewTime.value)) return
    if (hasPendingSegment.value) return
    seek(previewTime.value)
  }

  const releaseProgressPointerCapture = () => {
    const progressArea = progressAreaRef.value
    if (!progressArea || activeProgressPointerId === null || typeof progressArea.hasPointerCapture !== 'function') return

    if (!progressArea.hasPointerCapture(activeProgressPointerId)) return

    try {
      progressArea.releasePointerCapture(activeProgressPointerId)
    } catch {
      // Ignore browsers that reject release when the capture is already gone.
    }
  }

  const addProgressScrubListeners = () => {
    window.addEventListener('pointermove', onWindowProgressPointerMove)
    window.addEventListener('pointerup', onWindowProgressPointerUp)
    window.addEventListener('pointercancel', onWindowProgressPointerUp)
  }

  const removeProgressScrubListeners = () => {
    window.removeEventListener('pointermove', onWindowProgressPointerMove)
    window.removeEventListener('pointerup', onWindowProgressPointerUp)
    window.removeEventListener('pointercancel', onWindowProgressPointerUp)
  }

  const stopProgressScrub = (pointerId?: number) => {
    if (activeProgressPointerId !== null && typeof pointerId === 'number' && pointerId !== activeProgressPointerId) return

    releaseProgressPointerCapture()
    removeProgressScrubListeners()
    activeProgressPointerId = null
    isScrubbing.value = false
  }

  const onWindowProgressPointerMove = (e: PointerEvent) => {
    if (!isScrubbing.value) return
    if (activeProgressPointerId !== null && e.pointerId !== activeProgressPointerId) return

    updateProgressPreview(e)
  }

  const onWindowProgressPointerUp = (e: PointerEvent) => {
    if (activeProgressPointerId !== null && e.pointerId !== activeProgressPointerId) return
    // Commit once when the drag/click ends so DASH only rebuffers at the final time.
    if (isScrubbing.value) {
      commitScrubSeek()
    }
    stopProgressScrub(e.pointerId)
  }

  const onProgressPointerDown = (e: PointerEvent) => {
    activeProgressPointerId = e.pointerId
    isScrubbing.value = true
    addProgressScrubListeners()
    const progressArea = progressAreaRef.value
    if (progressArea && typeof progressArea.setPointerCapture === 'function') {
      try {
        progressArea.setPointerCapture(e.pointerId)
      } catch {
        // Ignore browsers that do not support capturing this pointer.
      }
    }
    updateProgressPreview(e)
  }

  const onProgressPointerMove = (e: PointerEvent) => {
    if (isScrubbing.value) return
    updateProgressPreview(e)
  }

  const onProgressPointerUp = (e?: PointerEvent) => {
    if (e && activeProgressPointerId !== null && e.pointerId !== activeProgressPointerId) return
    if (isScrubbing.value) {
      commitScrubSeek()
    }
    stopProgressScrub(e?.pointerId)
  }
  const onProgressPointerLeave = () => { if (!isScrubbing.value) previewTime.value = null }

  const clearPreview = () => { previewTime.value = null }

  const cleanup = () => {
    releaseProgressPointerCapture()
    removeProgressScrubListeners()
  }

  return {
    progressAreaRef,
    previewTime,
    previewPercent,
    isScrubbing,
    onProgressPointerDown,
    onProgressPointerMove,
    onProgressPointerUp,
    onProgressPointerLeave,
    clearPreview,
    cleanup,
  }
}

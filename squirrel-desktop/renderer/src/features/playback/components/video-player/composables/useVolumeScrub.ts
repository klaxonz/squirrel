import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import type { IconName } from '../core/useIcons'

/**
 * Volume display + pointer-scrub interaction.
 *
 * Pulls together the three concerns that were loose consts in VideoPlayer.vue:
 *   1. the volume display computeds (icon / text / fill percent),
 *   2. the pointer-drag scrub over the volume rail (pointerdown→move→up),
 *   3. the "show a central HUD only when the change came from the user, not
 *      programmatic volume restores" watcher (`pendingUserVolumeHud`).
 *
 * The composable owns `setUserVolume` (the user-initiated entry point) so the
 * HUD-suppression intent can't drift from the setVolume call. Programmatic
 * callers that don't want the HUD use `setVolume` directly.
 */
export interface UseVolumeScrubOptions {
  volume: Ref<number>
  isMuted: ComputedRef<boolean> | Ref<boolean>
  /** Programmatic volume setter from the player engine (no HUD side-effect). */
  setVolume: (value: number) => void
  showCentralHud: (type: string, value: string, icon: IconName, percent?: number) => void
  maxVolume?: number
}

export interface UseVolumeScrubReturn {
  volumeRailRef: Ref<HTMLElement | null>
  isVolumeScrubbing: Ref<boolean>
  isVolumeHovered: Ref<boolean>
  volumeIconName: ComputedRef<IconName>
  volumeText: ComputedRef<string>
  volumeFillPercent: ComputedRef<number>
  /** User-initiated volume set; arms the one-shot HUD-suppression flag. */
  setUserVolume: (value: number) => void
  onVolumePointerDown: (e: PointerEvent) => void
  onVolumePointerMove: (e: PointerEvent) => void
  onVolumePointerUp: (e?: PointerEvent) => void
  cleanup: () => void
}

export function useVolumeScrub(options: UseVolumeScrubOptions): UseVolumeScrubReturn {
  const { volume, isMuted, setVolume, showCentralHud, maxVolume = 200 } = options

  const volumeRailRef = ref<HTMLElement | null>(null)
  const isVolumeScrubbing = ref(false)
  const isVolumeHovered = ref(false)
  // One-shot: set just before a user-driven setVolume so the volume watcher can
  // tell "this change came from the user" apart from engine/restore writes, and
  // only then surface the central HUD. Null = don't show HUD.
  const pendingUserVolumeHud = ref<number | null>(null)
  let activeVolumePointerId: number | null = null

  const volumeIconName = computed<IconName>(() =>
    isMuted.value || volume.value === 0 ? 'volumeOff' : volume.value < 50 ? 'volumeLow' : 'volumeHigh',
  )
  const volumeText = computed(() => (isMuted.value ? 'Muted' : `${Math.round(volume.value)}%`))
  const volumeFillPercent = computed(() =>
    isMuted.value ? 0 : Math.min(100, (volume.value / maxVolume) * 100),
  )

  const setUserVolume = (value: number) => {
    pendingUserVolumeHud.value = value
    setVolume(value)
  }

  const updateVol = (e: PointerEvent) => {
    const rail = volumeRailRef.value
    if (!rail) return
    const rect = rail.getBoundingClientRect()
    if (rect.width <= 0) return
    setUserVolume(Math.max(0, Math.min(maxVolume, ((e.clientX - rect.left) / rect.width) * maxVolume)))
  }

  const releaseVolumePointerCapture = () => {
    const rail = volumeRailRef.value
    if (!rail || activeVolumePointerId === null || typeof rail.hasPointerCapture !== 'function') return
    if (!rail.hasPointerCapture(activeVolumePointerId)) return
    try {
      rail.releasePointerCapture(activeVolumePointerId)
    } catch {
      // Capture may already be gone.
    }
  }

  const addVolumeListeners = () => {
    window.addEventListener('pointermove', onWindowVolumePointerMove)
    window.addEventListener('pointerup', onWindowVolumePointerUp)
    window.addEventListener('pointercancel', onWindowVolumePointerUp)
  }

  const removeVolumeListeners = () => {
    window.removeEventListener('pointermove', onWindowVolumePointerMove)
    window.removeEventListener('pointerup', onWindowVolumePointerUp)
    window.removeEventListener('pointercancel', onWindowVolumePointerUp)
  }

  const stopVolumeScrub = (pointerId?: number) => {
    if (activeVolumePointerId !== null && typeof pointerId === 'number' && pointerId !== activeVolumePointerId) return
    releaseVolumePointerCapture()
    removeVolumeListeners()
    activeVolumePointerId = null
    isVolumeScrubbing.value = false
  }

  const onWindowVolumePointerMove = (e: PointerEvent) => {
    if (!isVolumeScrubbing.value) return
    if (activeVolumePointerId !== null && e.pointerId !== activeVolumePointerId) return
    updateVol(e)
  }

  const onWindowVolumePointerUp = (e: PointerEvent) => {
    stopVolumeScrub(e.pointerId)
  }

  const onVolumePointerDown = (e: PointerEvent) => {
    activeVolumePointerId = e.pointerId
    isVolumeScrubbing.value = true
    addVolumeListeners()
    const rail = volumeRailRef.value
    if (rail && typeof rail.setPointerCapture === 'function') {
      try {
        rail.setPointerCapture(e.pointerId)
      } catch {
        // Ignore browsers that reject capture for this pointer.
      }
    }
    updateVol(e)
  }

  const onVolumePointerMove = (e: PointerEvent) => {
    // Element-local move is only useful before window listeners / capture take over.
    if (isVolumeScrubbing.value) updateVol(e)
  }

  const onVolumePointerUp = (e?: PointerEvent) => {
    stopVolumeScrub(e?.pointerId)
  }

  const cleanup = () => {
    stopVolumeScrub()
  }

  // Only react to a change we can attribute to the user (pendingUserVolumeHud
  // was armed and the resulting volume matches it within rounding). Sub-0.1
  // deltas are noise from float quantisation and are ignored, matching the
  // original inline filter.
  watch(volume, (newVol, oldVol) => {
    if (Math.abs(newVol - oldVol) < 0.1) return
    const expectedVolume = pendingUserVolumeHud.value
    pendingUserVolumeHud.value = null
    if (expectedVolume === null || Math.abs(newVol - expectedVolume) > 0.1) return
    showCentralHud('volume', `${Math.round(newVol)}%`, volumeIconName.value, newVol)
  })

  return {
    volumeRailRef,
    isVolumeScrubbing,
    isVolumeHovered,
    volumeIconName,
    volumeText,
    volumeFillPercent,
    setUserVolume,
    onVolumePointerDown,
    onVolumePointerMove,
    onVolumePointerUp,
    cleanup,
  }
}

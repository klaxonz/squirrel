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
  isVolumeScrubbing: Ref<boolean>
  isVolumeHovered: Ref<boolean>
  volumeIconName: ComputedRef<IconName>
  volumeText: ComputedRef<string>
  volumeFillPercent: ComputedRef<number>
  /** User-initiated volume set; arms the one-shot HUD-suppression flag. */
  setUserVolume: (value: number) => void
  onVolumePointerDown: (e: PointerEvent) => void
  onVolumePointerMove: (e: PointerEvent) => void
  onVolumePointerUp: () => void
}

export function useVolumeScrub(options: UseVolumeScrubOptions): UseVolumeScrubReturn {
  const { volume, isMuted, setVolume, showCentralHud, maxVolume = 200 } = options

  const isVolumeScrubbing = ref(false)
  const isVolumeHovered = ref(false)
  // One-shot: set just before a user-driven setVolume so the volume watcher can
  // tell "this change came from the user" apart from engine/restore writes, and
  // only then surface the central HUD. Null = don't show HUD.
  const pendingUserVolumeHud = ref<number | null>(null)

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
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setUserVolume(Math.max(0, Math.min(maxVolume, ((e.clientX - rect.left) / rect.width) * maxVolume)))
  }

  const onVolumePointerDown = (e: PointerEvent) => {
    isVolumeScrubbing.value = true
    updateVol(e)
  }
  const onVolumePointerMove = (e: PointerEvent) => {
    if (isVolumeScrubbing.value) updateVol(e)
  }
  const onVolumePointerUp = () => {
    isVolumeScrubbing.value = false
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
    isVolumeScrubbing,
    isVolumeHovered,
    volumeIconName,
    volumeText,
    volumeFillPercent,
    setUserVolume,
    onVolumePointerDown,
    onVolumePointerMove,
    onVolumePointerUp,
  }
}

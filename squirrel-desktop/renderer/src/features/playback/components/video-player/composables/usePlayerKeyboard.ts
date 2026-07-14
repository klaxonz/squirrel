import { onMounted, onUnmounted, type ComputedRef, type Ref } from 'vue'
import type { IconName } from '../core/useIcons'
import type { KeyboardShortcutsConfig } from '../runtime/keyboardShortcuts'

export interface UsePlayerKeyboardOptions {
  keyboardShortcuts: Required<KeyboardShortcutsConfig>
  /** Reactive refs the handler reads. */
  currentTime: Ref<number>
  volume: Ref<number>
  isFullscreen: ComputedRef<boolean> | Ref<boolean>
  hasPendingSegment: ComputedRef<boolean>
  hasPrev: ComputedRef<boolean> | Ref<boolean> | boolean
  hasNext: ComputedRef<boolean> | Ref<boolean> | boolean
  /** Player store (loop AB state, playback rate). */
  store: {
    playbackRate: number
    loopAPoint: number | null
    abLoopActive: boolean
    setAbLoopActive: (v: boolean) => void
    setLoopAPoint: (v: number | null) => void
    setLoopBPoint: (v: number | null) => void
  }
  /** Rate ladder handed to the settings menu; index walk for speed up/down. */
  playbackRates: number[]
  /** i18n + HUD. */
  t: (key: string, params?: Record<string, string | number>) => string
  showCentralHud: (type: string, value: string, icon: IconName) => void
  /** Toggle-only side effect for the stats overlay visibility. */
  toggleStats: () => void
  /** Transport / volume actions. */
  togglePlay: () => void
  toggleFullscreen: () => void
  rotateVideo: () => void
  seek: (time: number) => void
  setUserVolume: (value: number) => void
  /** Subtitle quick-toggle. */
  toggleSubtitlesQuick: () => void
  /** Capture + save a frame (fullscreen-only via key). */
  captureScreenshot: () => void
  /** Clip-marker segment actions. */
  startSegmentCapture: () => void
  finishSegmentCapture: () => void
  cancelSegmentCapture: () => void
  markCurrentPoint: () => void
  /** Apply a new playback rate. */
  handleSpeedSelect: (rate: number) => void
  /** Playlist navigation. */
  onPrev: () => void
  onNext: () => void
  /** Max volume ceiling used by volume up/down stepping. */
  maxVolume: number
}

/**
 * Wires the player keyboard-shortcut table to a `window` keydown listener and
 * owns its lifecycle. The action surface is injected so this composable stays a
 * pure dispatch table — no player state of its own.
 */
export function usePlayerKeyboard(options: UsePlayerKeyboardOptions): { handleKeyDown: (e: KeyboardEvent) => void } {
  const {
    keyboardShortcuts, currentTime, volume, isFullscreen, hasPendingSegment, hasPrev, hasNext,
    store, playbackRates, t, showCentralHud, toggleStats,
    togglePlay, toggleFullscreen, rotateVideo, seek, setUserVolume,
    toggleSubtitlesQuick, captureScreenshot,
    startSegmentCapture, finishSegmentCapture, cancelSegmentCapture, markCurrentPoint,
    handleSpeedSelect, onPrev, onNext, maxVolume,
  } = options

  const isModifierKey = (e: KeyboardEvent): boolean =>
    e.metaKey || e.ctrlKey || e.altKey

  const isInputFocused = (): boolean =>
    document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA'

  const hasPrevValue = (): boolean =>
    typeof hasPrev === 'boolean' ? hasPrev : hasPrev.value
  const hasNextValue = (): boolean =>
    typeof hasNext === 'boolean' ? hasNext : hasNext.value

  const handleKeyDown = (e: KeyboardEvent) => {
    const ks = keyboardShortcuts
    if (!ks.enabled) return
    if (isModifierKey(e)) return

    const matches = (key: string): boolean => {
      if (e.key === key) return true
      if (key === ' ' && e.code === 'Space') return true
      return false
    }

    if (matches(ks.playPause)) { e.preventDefault(); togglePlay(); return }
    if (matches(ks.fullscreen)) { toggleFullscreen(); return }

    if (matches(ks.rotate)) {
      if (isInputFocused()) return
      e.preventDefault()
      rotateVideo()
      return
    }

    if (matches(ks.seekBackward)) { e.preventDefault(); seek(currentTime.value - 10); return }
    if (matches(ks.seekForward)) { e.preventDefault(); seek(currentTime.value + 10); return }
    if (matches(ks.volumeUp)) { e.preventDefault(); setUserVolume(Math.min(maxVolume, volume.value + 5)); return }
    if (matches(ks.volumeDown)) { e.preventDefault(); setUserVolume(Math.max(0, volume.value - 5)); return }

    if (matches(ks.markSegmentStart)) {
      if (isInputFocused()) return
      e.preventDefault()
      if (e.shiftKey) {
        if (hasPendingSegment.value) finishSegmentCapture()
        else startSegmentCapture()
        return
      }
      if (matches(ks.markPoint)) {
        markCurrentPoint()
        return
      }
    }

    if (matches(ks.markPoint)) {
      if (isInputFocused()) return
      e.preventDefault()
      markCurrentPoint()
      return
    }

    if (matches(ks.cancelSegment) && hasPendingSegment.value) {
      cancelSegmentCapture()
      return
    }

    if (matches(ks.toggleSubtitles)) {
      if (isInputFocused()) return
      e.preventDefault()
      toggleSubtitlesQuick()
      return
    }

    if (matches(ks.toggleStats)) {
      if (isInputFocused()) return
      e.preventDefault()
      toggleStats()
      return
    }

    if (matches(ks.screenshot) && isFullscreen.value) {
      e.preventDefault()
      captureScreenshot()
      return
    }

    if (matches(ks.speedUp)) {
      e.preventDefault()
      const nextIdx = playbackRates.indexOf(store.playbackRate) + 1
      if (nextIdx < playbackRates.length) handleSpeedSelect(playbackRates[nextIdx])
      return
    }

    if (matches(ks.speedDown)) {
      e.preventDefault()
      const prevIdx = playbackRates.indexOf(store.playbackRate) - 1
      if (prevIdx >= 0) handleSpeedSelect(playbackRates[prevIdx])
      return
    }

    if (matches(ks.setLoopA) && isFullscreen.value) {
      e.preventDefault()
      store.setAbLoopActive(false)
      store.setLoopAPoint(currentTime.value)
      store.setLoopBPoint(null)
      showCentralHud('loopAB', t('loopSetA'), 'skipBackward')
      return
    }

    if (matches(ks.setLoopB) && isFullscreen.value && store.loopAPoint !== null) {
      e.preventDefault()
      const bTime = currentTime.value
      if (bTime <= (store.loopAPoint ?? 0)) return
      store.setLoopBPoint(bTime)
      store.setAbLoopActive(true)
      showCentralHud('loopAB', t('abLoopActive'), 'loop')
      return
    }

    if (matches(ks.clearLoopAB) && isFullscreen.value && store.abLoopActive) {
      e.preventDefault()
      store.setAbLoopActive(false)
      store.setLoopAPoint(null)
      store.setLoopBPoint(null)
      showCentralHud('loopAB', t('loopClearAB'), 'loop')
      return
    }

    if (matches(ks.prevVideo) && hasPrevValue()) {
      e.preventDefault()
      onPrev()
      return
    }

    if (matches(ks.nextVideo) && hasNextValue()) {
      e.preventDefault()
      onNext()
      return
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
  })
  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
  })

  return { handleKeyDown }
}

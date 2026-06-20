import { onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { Logger } from '@/shared/lib/logger'
import type { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

/**
 * Bridge between a single `<audio>` element and the music player store.
 *
 * Owns the element ref, the mount/unmount `setAudioRef` registration, and the
 * `audioSrc` watcher that drives the element's imperative lifecycle: set
 * src + volume + play on a new source, or clear src + load + sync state when it
 * goes away. The ref + watcher are wired so the store always sees the live
 * element (template rebind, hot reload) and so a play() rejection surfaces as a
 * playback error rather than an unhandled promise.
 *
 * Extracted from GlobalMusicPlayerBar.vue so the imperative audio-element
 * lifecycle — the riskiest part of the player, where a forgotten load() or an
 * unhandled play() rejection lives — is isolated and auditable rather than
 * interleaved with bar wiring.
 */
export interface UseAudioElementBridgeOptions {
  store: ReturnType<typeof useMusicPlayerStore>
}

export interface UseAudioElementBridgeReturn {
  /** Template ref: attach to the `<audio>` element. */
  audioEl: Ref<HTMLAudioElement | null>
}

export function useAudioElementBridge(options: UseAudioElementBridgeOptions): UseAudioElementBridgeReturn {
  const { store } = options

  const audioEl = ref<HTMLAudioElement | null>(null)

  onMounted(() => {
    store.setAudioRef(audioEl.value)
  })

  // Re-register whenever the template rebinds the ref (e.g. conditional render),
  // so the store never points at a detached element.
  watch(audioEl, (el) => {
    store.setAudioRef(el)
  })

  // Drive the element's imperative lifecycle from the store's audio source.
  watch(
    () => store.audioSrc,
    (src) => {
      const el = audioEl.value
      if (!el) return

      if (src) {
        el.src = src
        el.volume = store.volume
        el.play().catch((err) => {
          store.markPlaybackError('播放失败，当前歌曲可能不可播放')
          Logger.error('Failed to play music audio', err)
        })
      } else {
        // Clearing the source: drop the attribute (not just empty src, which
        // some browsers treat as "keep playing") and force a load so the
        // element resets, then let the store reconcile its playing state.
        el.removeAttribute('src')
        el.load()
        store.syncPlayState()
      }
    },
  )

  onUnmounted(() => {
    store.setAudioRef(null)
  })

  return {
    audioEl,
  }
}

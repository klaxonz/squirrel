import { onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'

/**
 * IntersectionObserver-backed infinite-scroll sentinel.
 *
 * The same "observe a sentinel element, fire a callback when it intersects,
 * bound to the app's main scroll root" pattern was copy-pasted across at least
 * three video-feed components (VideoList, RemoteSearchResults,
 * RemoteChannelVideoGrid), each with its own onMounted/onUnmounted observer +
 * disconnect lifecycle. This composable owns that lifecycle once.
 *
 * `onIntersect` fires whenever the sentinel becomes visible (the caller applies
 * its own loading / allLoaded guards inside the callback). The observer is
 * (re)bound on mount and whenever the sentinel ref rebinds (e.g. v-if swap),
 * and always disconnected on unmount — so a re-render can't leak a stale
 * observer or miss the new sentinel.
 *
 * @param sentinel  template ref attached to the sentinel element
 * @param onIntersect  fired when the sentinel intersects the scroll root
 * @param rootMargin  observer rootMargin; defaults to '600px' (preload band)
 * @param root  explicit observer root; defaults to the app main scroll container
 */
export interface UseInfiniteScrollSentinelOptions {
  sentinel: Ref<HTMLElement | null>
  onIntersect: () => void
  rootMargin?: string
  root?: HTMLElement | null
}

export function useInfiniteScrollSentinel(options: UseInfiniteScrollSentinelOptions): void {
  const { sentinel, onIntersect, rootMargin = '600px', root } = options

  let observer: IntersectionObserver | null = null

  const resolveRoot = (): HTMLElement | null => root ?? getMainScrollRoot()

  const bind = () => {
    observer?.disconnect()
    observer = null

    const el = sentinel.value
    if (!el) return

    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) onIntersect()
      },
      { root: resolveRoot(), rootMargin },
    )
    observer.observe(el)
  }

  onMounted(bind)
  // Re-bind when the sentinel ref rebinds (conditional render / route swap) so
  // the observer always tracks the live element.
  watch(sentinel, bind)
  onUnmounted(() => observer?.disconnect())
}

/** Convenience: a ready-to-attach sentinel ref + the observer, for components
 *  that don't already have a trigger ref. */
export function useInfiniteScrollSentinelRef(
  onIntersect: () => void,
  rootMargin?: string,
  root?: HTMLElement | null,
): { sentinel: Ref<HTMLElement | null> } {
  const sentinel = ref<HTMLElement | null>(null)
  useInfiniteScrollSentinel({ sentinel, onIntersect, rootMargin, root })
  return { sentinel }
}

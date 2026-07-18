import { computed, onMounted, onUnmounted, ref, shallowRef, toValue, watch, type MaybeRefOrGetter, type Ref } from 'vue'

/**
 * Options for sizing a loading skeleton grid to the visible viewport.
 *
 * The column count is derived from the SAME formula the CSS auto-fill grid
 * uses (`repeat(auto-fill, minmax(min(100%, minCardWidth), 1fr))`), so the
 * skeleton grid and the real card grid always agree on column count without
 * any hand-mirrored breakpoint table. This was the root cause of the previous
 * drift: 5 call-sites each declared a `GridBreakpoint[]` that had to "mirror"
 * the `grid-cols-*` classes, and they desynced every time the classes changed.
 */
export interface SkeletonCountOptions {
  /**
   * Minimum card width in px — MUST match the `--app-grid-min` the grid is
   * rendered with (defaults to `--app-video-grid-min`, 320px). Used to compute
   * the auto-fill column count: `cols = floor((width + gap) / (min + gap))`.
   * Set to a very large number (e.g. Number.MAX_SAFE_INTEGER) for single-column
   * layouts (list view).
   */
  minCardWidth?: MaybeRefOrGetter<number>
  /** Horizontal+vertical gap between cells in px (matches the grid `gap`). */
  gap?: MaybeRefOrGetter<number>
  /** Approximate card height in px. */
  cardHeight?: MaybeRefOrGetter<number>
  /** Hard floor so very short viewports still look populated. */
  min?: MaybeRefOrGetter<number>
  /** Hard ceiling so huge viewports don't render absurd skeletons. */
  max?: MaybeRefOrGetter<number>
  /** Extra rows to render below the fold for a smoother scroll-in. */
  overscanRows?: MaybeRefOrGetter<number>
}

const DEFAULTS = {
  minCardWidth: 320,
  gap: 24,
  cardHeight: 220,
  min: 4,
  max: 30,
  overscanRows: 1,
} as const

const clamp = (value: number, lo: number, hi: number) =>
  Math.min(hi, Math.max(lo, value))

/**
 * Returns a reactive skeleton count sized to fill the visible viewport for a
 * CSS `auto-fill` card grid. Pass the returned `attachRef` to the grid's root
 * so the column count tracks the actual container width (not the full window).
 */
export function useSkeletonCount(options: SkeletonCountOptions = {}) {
  const {
    minCardWidth = DEFAULTS.minCardWidth,
    gap = DEFAULTS.gap,
    cardHeight = DEFAULTS.cardHeight,
    min = DEFAULTS.min,
    max = DEFAULTS.max,
    overscanRows = DEFAULTS.overscanRows,
  } = options

  const attachRef = ref<HTMLElement | null>(null)
  const containerWidth = shallowRef<number>(
    typeof window !== 'undefined' ? window.innerWidth : 1280,
  )
  const viewportHeight = shallowRef<number>(
    typeof window !== 'undefined' ? window.innerHeight : 800,
  )

  // Mirror CSS `repeat(auto-fill, minmax(min(100%, minCardWidth), 1fr))`:
  // the browser lays out N columns where N is the largest integer satisfying
  // N*min + (N-1)*gap <= width, i.e. N = floor((width + gap) / (min + gap)).
  const columns = computed(() => {
    const w = containerWidth.value
    const minW = toValue(minCardWidth)
    const g = toValue(gap)
    if (w <= 0 || minW <= 0) return 1
    return Math.max(1, Math.floor((w + g) / (minW + g)))
  })

  const count = computed(() => {
    const cols = columns.value
    const h = toValue(cardHeight)
    const gapPx = toValue(gap)
    const overscan = toValue(overscanRows)
    const rows = Math.ceil(
      (viewportHeight.value + overscan * (h + gapPx)) / (h + gapPx),
    )
    return clamp(cols * rows, toValue(min), toValue(max))
  })

  let resizeObserver: ResizeObserver | null = null

  const onWindowResize = () => {
    viewportHeight.value = window.innerHeight
    // Fallback path when ResizeObserver isn't attached: keep width in sync.
    if (!resizeObserver) {
      containerWidth.value = window.innerWidth
    }
  }

  onMounted(() => {
    viewportHeight.value = window.innerHeight
    window.addEventListener('resize', onWindowResize, { passive: true })

    if (typeof ResizeObserver !== 'undefined' && attachRef.value) {
      resizeObserver = new ResizeObserver((entries) => {
        const entry = entries[0]
        if (entry) containerWidth.value = entry.contentRect.width
      })
      resizeObserver.observe(attachRef.value)
      // Seed synchronously in case the observer fires after first paint.
      containerWidth.value = attachRef.value.clientWidth
    } else {
      // No RO support: keep using window.innerWidth as a fallback.
      containerWidth.value = window.innerWidth
    }
  })

  // If the ref binds after mount (e.g. inside a v-if subtree), start observing.
  watch(attachRef, (node, prev) => {
    if (prev && resizeObserver) resizeObserver.unobserve(prev)
    if (node && typeof ResizeObserver !== 'undefined') {
      if (!resizeObserver) {
        resizeObserver = new ResizeObserver((entries) => {
          const entry = entries[0]
          if (entry) containerWidth.value = entry.contentRect.width
        })
      }
      resizeObserver.observe(node)
      containerWidth.value = node.clientWidth
    }
  })

  onUnmounted(() => {
    window.removeEventListener('resize', onWindowResize)
    resizeObserver?.disconnect()
    resizeObserver = null
  })

  return { count, columns, attachRef }
}

export type SkeletonCountReturn = {
  count: Ref<number>
  columns: Ref<number>
  attachRef: Ref<HTMLElement | null>
}

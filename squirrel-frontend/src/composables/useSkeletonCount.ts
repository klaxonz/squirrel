import { computed, onMounted, onUnmounted, ref, shallowRef, toValue, watch, type MaybeRefOrGetter, type Ref } from 'vue'

/**
 * A breakpoint entry: `[minWidthPx, columnCount]`. Descending order expected.
 * Mirror the `grid-cols-*` classes used in the component template.
 */
export type GridBreakpoint = [number, number]

export interface SkeletonCountOptions {
  /**
   * Breakpoints used to derive the grid column count from container width.
   * Must be sorted descending by width, e.g. `[[1920, 6], [1536, 5], [0, 1]]`.
   * Accepts a ref/getter so the layout can change reactively (e.g. list/grid).
   */
  breakpoints: MaybeRefOrGetter<GridBreakpoint[]>
  /** Approximate card height in px. */
  cardHeight?: MaybeRefOrGetter<number>
  /** Vertical gap between rows in px (matches Tailwind `gap-*`). */
  rowGap?: MaybeRefOrGetter<number>
  /** Hard floor so very short viewports still look populated. */
  min?: MaybeRefOrGetter<number>
  /** Hard ceiling so huge viewports don't render absurd skeletons. */
  max?: MaybeRefOrGetter<number>
  /** Extra rows to render below the fold for a smoother scroll-in. */
  overscanRows?: MaybeRefOrGetter<number>
}

const DEFAULTS = {
  cardHeight: 220,
  rowGap: 24,
  min: 4,
  max: 30,
  overscanRows: 1,
} as const

const clamp = (value: number, lo: number, hi: number) =>
  Math.min(hi, Math.max(lo, value))

/**
 * Returns a reactive skeleton count sized to fill the visible viewport for the
 * given responsive grid. Pass the returned `attachRef` to the grid's root so the
 * column count tracks the actual container width (not the full window).
 */
export function useSkeletonCount(options: SkeletonCountOptions) {
  const {
    breakpoints,
    cardHeight = DEFAULTS.cardHeight,
    rowGap = DEFAULTS.rowGap,
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

  const columns = computed(() => {
    const w = containerWidth.value
    const bps = toValue(breakpoints)
    for (const [bp, cols] of bps) {
      if (w >= bp) return Math.max(1, cols)
    }
    return 1
  })

  const count = computed(() => {
    const cols = columns.value
    const h = toValue(cardHeight)
    const gap = toValue(rowGap)
    const overscan = toValue(overscanRows)
    const rows = Math.ceil(
      (viewportHeight.value + overscan * (h + gap)) / (h + gap),
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

/** Convenience: builds a breakpoints array from Tailwind-style `min:cols` pairs. */
export function sortBreakpoints(entries: GridBreakpoint[]): GridBreakpoint[] {
  return [...entries].sort((a, b) => b[0] - a[0])
}

export type SkeletonCountReturn = {
  count: Ref<number>
  columns: Ref<number>
  attachRef: Ref<HTMLElement | null>
}


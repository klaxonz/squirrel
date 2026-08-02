import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'

type Id = string | number

export type NewContentDetectorOptions<T> = {
  /** Latest known marker — usually the id of the first (newest) list item. */
  getKnownId: () => Id | null
  /**
   * Silent fetch of the newest page. MUST NOT mutate visible state — the
   * caller only prepends on apply, so the baseline comparison stays honest.
   */
  fetchNewest: () => Promise<T[]>
  /** Stable id extractor for a fetched item. */
  idOf: (item: T) => Id
  /** Runs when the user clicks the bar; receives the detected new items. */
  onApply: (newItems: T[]) => void | Promise<void>
  /** Opt-out gate (inactive tab, loading, error state…). */
  isEnabled?: () => boolean
  /**
   * Custom "does this page contain new content?" check. Default: the fetched
   * page's first id differs from the known marker. Used by pages whose list is
   * not strictly newest-first (e.g. reorderable playlists).
   */
  hasNew?: (items: T[]) => boolean
  /** Custom count override; default: number of fetched items ahead of the marker. */
  countOf?: (items: T[], knownId: Id) => number
  /** Scroll container that auto-dismisses the bar on user scroll. */
  getScrollContainer?: () => HTMLElement | null
  /** Coalescing delay for check(); default 400ms. */
  debounceMs?: number
  /** Min gap between background (mount/visibility) checks; default 30s. */
  backgroundThresholdMs?: number
  /** Delay after mount before the baseline check; default 1200ms. */
  initialDelayMs?: number
}

/**
 * Reddit-style "view N new posts" detection.
 *
 * Silently fetches the newest page, compares its leading marker against the
 * currently displayed list, and surfaces a bar instead of mutating the list.
 * The list is only touched on apply, so browsing is never interrupted.
 */
export function useNewContentDetector<T>(options: NewContentDetectorOptions<T>) {
  const visible = ref(false)
  const count = ref(0)

  let pendingItems: T[] = []
  let checking = false
  let debounceTimer: ReturnType<typeof setTimeout> | undefined
  let initialTimer: ReturnType<typeof setTimeout> | undefined
  let lastBackgroundCheckAt = Date.now()
  let scrollTarget: HTMLElement | null = null

  const resolveCount = (items: T[], knownId: Id): number => {
    if (options.countOf) return options.countOf(items, knownId)
    const knownIndex = items.findIndex((item) => String(options.idOf(item)) === String(knownId))
    if (knownIndex === -1) return items.length
    return knownIndex
  }

  const resolveNewItems = (items: T[], knownId: Id): T[] => {
    if (options.hasNew) return items
    const knownIndex = items.findIndex((item) => String(options.idOf(item)) === String(knownId))
    if (knownIndex === -1) return items
    return items.slice(0, knownIndex)
  }

  const runCheck = async () => {
    if (checking || visible.value) return
    if (options.isEnabled && !options.isEnabled()) return

    const knownId = options.getKnownId()
    if (knownId == null || knownId === '') return

    checking = true
    try {
      const items = await options.fetchNewest()
      if (!items.length) return

      const defaultHasNew = () => String(options.idOf(items[0])) !== String(knownId)
      const hasNewContent = options.hasNew ? options.hasNew(items) : defaultHasNew()
      if (!hasNewContent) return

      const newItems = resolveNewItems(items, knownId)
      if (!newItems.length) return

      pendingItems = newItems
      count.value = resolveCount(items, knownId)
      visible.value = true
    } catch {
      // Silent by design — a failed background probe must never disturb the feed.
    } finally {
      checking = false
    }
  }

  /** Trigger a (debounced) background probe. Safe to call from any event. */
  const check = () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      void runCheck()
    }, options.debounceMs ?? 400)
  }

  /** User clicked the bar: insert the pending items, then hide. */
  const apply = async () => {
    if (!visible.value || !pendingItems.length) return
    const items = pendingItems
    pendingItems = []
    visible.value = false
    count.value = 0
    await options.onApply(items)
  }

  /** Hide without applying (user scrolled / switched context). */
  const dismiss = () => {
    visible.value = false
  }

  /** Full reset — used on tab/filter switches where pending items go stale. */
  const reset = () => {
    dismiss()
    pendingItems = []
    count.value = 0
  }

  const handleVisibilityChange = () => {
    if (document.hidden) return
    if (Date.now() - lastBackgroundCheckAt < (options.backgroundThresholdMs ?? 30_000)) return
    lastBackgroundCheckAt = Date.now()
    check()
  }

  const handleScroll = () => {
    if (visible.value) dismiss()
  }

  const attachScrollListener = () => {
    scrollTarget = options.getScrollContainer ? options.getScrollContainer() : getMainScrollRoot()
    scrollTarget?.addEventListener('scroll', handleScroll, { passive: true })
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    attachScrollListener()
    // Baseline probe: after the page's own initial load settles, one quiet
    // fetch establishes the marker. No bar when the page is already fresh.
    initialTimer = setTimeout(() => {
      void runCheck()
    }, options.initialDelayMs ?? 1200)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    scrollTarget?.removeEventListener('scroll', handleScroll)
    if (debounceTimer) clearTimeout(debounceTimer)
    if (initialTimer) clearTimeout(initialTimer)
  })

  return { visible, count, check, apply, dismiss, reset }
}

/**
 * Insert content at the top of a feed while keeping the user's reading
 * position stable: record scrollTop/scrollHeight before, mutate, then shift
 * scrollTop by the inserted height. At the very top we snap to 0 instead so
 * the newly inserted items are revealed — matching Reddit's apply behaviour.
 */
export async function prependPreservingScroll(
  getContainer: () => HTMLElement | null,
  mutate: () => void | Promise<void>,
): Promise<void> {
  const container = getContainer()
  const prevScrollTop = container?.scrollTop ?? 0
  const prevScrollHeight = container?.scrollHeight ?? 0

  await mutate()
  await nextTick()

  const target = getContainer()
  if (!target) return
  const delta = Math.max(0, target.scrollHeight - prevScrollHeight)
  target.scrollTop = prevScrollTop <= 4 ? 0 : prevScrollTop + delta
}

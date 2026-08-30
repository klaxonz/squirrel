import { nextTick, onUnmounted, ref, watch, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  MAIN_ROUTE_SCROLL_KEY,
  applyRouteScrollPositions,
  collectRouteScrollPositions,
  type RouteScrollPositions,
} from '@/shared/lib/routeScrollRestoration'
import type { useNavigationHistory } from '@/shared/composables/useNavigationHistory'

type NavigationHistory = ReturnType<typeof useNavigationHistory>

type RouteScrollRestorationOptions = {
  layoutRef: Ref<HTMLElement | null>
  mainScrollRef: Ref<HTMLElement | null>
  navigation: Pick<NavigationHistory, 'current' | 'saveScrollPositions'>
}

/** Owns route scroll capture, restoration retries, and their lifecycle cleanup. */
export function useAppRouteScrollRestoration({
  layoutRef,
  mainScrollRef,
  navigation,
}: RouteScrollRestorationOptions) {
  const route = useRoute()
  let scrollSaveTimer: ReturnType<typeof setTimeout> | null = null
  // The outer scroll element survives route changes. Keep an explicit owner so
  // a delayed save can never write the previous page's offset into the new entry.
  let scrollOwnerEntryId: string | null = navigation.current.value?.id ?? null
  let scrollRestoreTimer: ReturnType<typeof setTimeout> | null = null
  let scrollRestoreToken = 0
  const isRestoringScroll = ref(false)

  function flushScrollPosition() {
    if (scrollSaveTimer) {
      clearTimeout(scrollSaveTimer)
      scrollSaveTimer = null
    }
    const layoutEl = layoutRef.value
    if (!layoutEl || !scrollOwnerEntryId) return
    navigation.saveScrollPositions(collectRouteScrollPositions(layoutEl), scrollOwnerEntryId)
  }

  function handleRouteScroll(event: Event) {
    if (isRestoringScroll.value) return
    const target = event.target
    if (!(target instanceof HTMLElement) || !target.dataset.routeScroll) return
    if (scrollSaveTimer) clearTimeout(scrollSaveTimer)
    scrollSaveTimer = setTimeout(() => {
      scrollSaveTimer = null
      flushScrollPosition()
    }, 120)
  }

  function cancelScrollRestoration() {
    scrollRestoreToken += 1
    isRestoringScroll.value = false
    if (scrollRestoreTimer) {
      clearTimeout(scrollRestoreTimer)
      scrollRestoreTimer = null
    }
  }

  function restoreScrollPositions(positions: RouteScrollPositions) {
    cancelScrollRestoration()
    const layoutEl = layoutRef.value
    if (!layoutEl) return

    const token = scrollRestoreToken
    const deadline = Date.now() + 5_000
    // Keep applying through the page crossfade. During the first frame the
    // leaving page can temporarily provide enough scroll height and make a
    // premature restore look successful; that height disappears ~180ms later.
    const settleUntil = Date.now() + 300
    isRestoringScroll.value = true

    const apply = () => {
      if (token !== scrollRestoreToken) return
      const complete = applyRouteScrollPositions(layoutEl, positions)
      if ((complete && Date.now() >= settleUntil) || Date.now() >= deadline) {
        isRestoringScroll.value = false
        scrollRestoreTimer = null
        return
      }
      scrollRestoreTimer = setTimeout(apply, 50)
    }
    apply()
  }

  watch(() => route.fullPath, async () => {
    // afterEach has already selected the destination history entry when this
    // watcher runs. Flush against the captured owner before restoring the new
    // page, otherwise a quick card click loses the list position.
    flushScrollPosition()
    await nextTick()
    const scrollEl = mainScrollRef.value
    if (!scrollEl) return
    // Use the entry's recorded positions rather than estimating from history.
    const entry = navigation.current.value
    scrollOwnerEntryId = entry?.id ?? null
    restoreScrollPositions({
      [MAIN_ROUTE_SCROLL_KEY]: entry?.scrollY ?? 0,
      ...entry?.scrollPositions,
    })
  })

  onUnmounted(() => {
    flushScrollPosition()
    cancelScrollRestoration()
  })

  return {
    handleRouteScroll,
    cancelScrollRestoration,
  }
}

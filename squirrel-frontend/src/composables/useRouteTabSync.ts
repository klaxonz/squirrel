import { onActivated, onDeactivated, onMounted, watch } from 'vue'
import type { Ref, WatchStopHandle } from 'vue'
import { VIDEO_TABS } from '../constants/videos'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

// Sync a tab ref with route path segment and push updates back to the router.
// Under keep-alive, multiple views (e.g. HomeView + ChannelDetailView) each
// instantiate this composable. The deactivated view's watcher must be paused,
// otherwise both fire on a tab change and the one with a null subscriptionId
// clobbers the correct route (e.g. pushes /videos/unread over /subscription/123/unread).
export function useRouteTabSync(
  router: Router,
  route: RouteLocationNormalizedLoaded,
  activeTabRef: Ref<string>,
  subscriptionIdRef?: Ref<string | number | null | undefined>
) {
  const tabValues = VIDEO_TABS.map(t => t.value)

  const setTabFromPath = (path: string) => {
    const segs = (path || '').split('/')
    const last = segs[segs.length - 1]
    if (tabValues.includes(last) && last !== activeTabRef.value) {
      activeTabRef.value = last
    }
  }

  const pushPathFromTab = (tab: string) => {
    const subId = subscriptionIdRef?.value
    const target = subId
      ? `/subscription/${subId}/${tab}`
      : `/videos/${tab}`
    if (router.currentRoute.value.fullPath !== target) {
      router.push(target)
    }
  }

  onMounted(() => {
    // initialize from current path
    setTabFromPath(router.currentRoute.value.path)
  })

  let tabWatchStop: WatchStopHandle | null = watch(() => activeTabRef.value, (tab) => {
    if (!tabValues.includes(tab)) return
    pushPathFromTab(tab)
  })

  const pathWatchStop = watch(() => route.path, (newPath) => {
    setTabFromPath(newPath)
  })

  // Pause tab->route pushing while deactivated so a cached sibling view does
  // not race the active one. Route->tab syncing (pathWatchStop) stays active.
  onActivated(() => {
    if (!tabWatchStop) {
      tabWatchStop = watch(() => activeTabRef.value, (tab) => {
        if (!tabValues.includes(tab)) return
        pushPathFromTab(tab)
      })
    }
    // Re-sync from current path in case route changed while inactive.
    setTabFromPath(router.currentRoute.value.path)
  })

  onDeactivated(() => {
    tabWatchStop?.()
    tabWatchStop = null
  })
}


import { onMounted, watch } from 'vue'
import type { Ref } from 'vue'
import { VIDEO_TABS } from '../constants/videos'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

// Sync a tab ref with route path segment and push updates back to the router
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
    const target = subscriptionIdRef?.value
      ? `/subscription/${subscriptionIdRef.value}/${tab}`
      : `/videos/${tab}`
    if (router.currentRoute.value.fullPath !== target) {
      router.push(target)
    }
  }

  onMounted(() => {
    // initialize from current path
    setTabFromPath(router.currentRoute.value.path)
  })

  watch(() => activeTabRef.value, (tab) => {
    if (!tabValues.includes(tab)) return
    pushPathFromTab(tab)
  })

  watch(() => route.path, (newPath) => {
    setTabFromPath(newPath)
  })
}

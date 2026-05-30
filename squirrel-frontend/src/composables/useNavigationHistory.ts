import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { findNavigationItemByKey } from '@/constants/sidebar'
import type { AppNavKey } from '@/constants/sidebar'

interface RouteSnapshot {
  fullPath: string
  name: string
  navKey: string
  sectionLabel: string
  pageTitle: string
}

// ── singleton state (shared across all composable instances) ──
let initialPath: string | null = null
const lastNonVideoRoute = ref<RouteSnapshot | null>(null)
const forwardDepth = ref(0)
let isInternalNavigation = false

const canGoForward = computed(() => forwardDepth.value > 0)

function captureRouteSnapshot(route: {
  fullPath: string
  name: string
  navKey: string
  sectionLabel: string
  pageTitle: string
}): RouteSnapshot {
  return {
    fullPath: route.fullPath,
    name: route.name,
    navKey: route.navKey,
    sectionLabel: route.sectionLabel,
    pageTitle: route.pageTitle,
  }
}

export function useNavigationHistory() {
  const router = useRouter()
  const route = useRoute()

  if (initialPath === null) {
    initialPath = route.path
  }

  const canGoBack = computed(() => route.path !== initialPath)

  async function goBack() {
    isInternalNavigation = true
    const pathBefore = route.fullPath
    try {
      await router.back()
    } catch {
      isInternalNavigation = false
      return
    }
    if (route.fullPath !== pathBefore) {
      forwardDepth.value++
    } else {
      // No history to go back to — reset
      isInternalNavigation = false
    }
  }

  async function goForward() {
    if (forwardDepth.value <= 0) return
    isInternalNavigation = true
    const pathBefore = route.fullPath
    try {
      await router.forward()
    } catch {
      forwardDepth.value = 0
      isInternalNavigation = false
      return
    }
    if (route.fullPath !== pathBefore) {
      forwardDepth.value = Math.max(0, forwardDepth.value - 1)
    } else {
      // No forward entries available — reset
      forwardDepth.value = 0
      isInternalNavigation = false
    }
  }

  watch(
    () => ({
      path: route.path,
      fullPath: route.fullPath,
      name: String(route.name || ''),
      navKey: String(route.meta?.navKey || ''),
      sectionLabel: String(route.meta?.sectionLabel || ''),
      pageTitle: String(route.meta?.title || ''),
    }),
    (current, previous) => {
      if (!previous || previous.path === current.path) return

      // User-initiated navigation (not via title bar back/forward)
      // invalidates the forward stack.
      if (!isInternalNavigation) {
        forwardDepth.value = 0
      }
      isInternalNavigation = false

      // Record the page the user came from when entering a video page.
      // Video-to-video navigation (via replace) should not overwrite the original source.
      if (current.name === 'VideoPlay' && previous.name !== 'VideoPlay') {
        lastNonVideoRoute.value = captureRouteSnapshot(previous)
      }
    },
  )

  const videoBackLabel = computed(() => {
    const ctx = lastNonVideoRoute.value
    if (!ctx) return null
    const navItem = findNavigationItemByKey(ctx.navKey as AppNavKey)
    const sectionName = navItem?.name || ctx.sectionLabel || ''

    // For the home feed section, show the specific tab name
    // (e.g. "未读视频") instead of the generic "首页".
    if (ctx.navKey === 'videos' && ctx.pageTitle && ctx.pageTitle !== navItem?.title) {
      return ctx.pageTitle
    }

    return sectionName || ctx.pageTitle || null
  })

  const videoBackTarget = computed((): RouteLocationRaw | null => {
    const ctx = lastNonVideoRoute.value
    if (!ctx) return null
    return ctx.fullPath
  })

  const isVideoPage = computed(() => route.name === 'VideoPlay')

  return {
    canGoBack,
    canGoForward,
    goBack,
    goForward,
    videoBackLabel,
    videoBackTarget,
    isVideoPage,
    lastNonVideoRoute,
  }
}

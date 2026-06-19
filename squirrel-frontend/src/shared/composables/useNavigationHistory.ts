import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { findNavigationItemByKey } from '@/shared/constants/sidebar'
import type { AppNavKey } from '@/shared/constants/sidebar'
import { Logger } from '@/shared/lib/logger'

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
const internalBackAvailable = ref(false)
let internalBackHandler: (() => boolean) | null = null

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

  const canGoBack = computed(() => internalBackAvailable.value || route.path !== initialPath)

  async function goBack() {
    if (internalBackAvailable.value && internalBackHandler?.()) {
      forwardDepth.value = 0
      return
    }
    isInternalNavigation = true
    const pathBefore = route.fullPath
    try {
      await router.back()
    } catch (err) {
      Logger.warn('[useNavigationHistory] goBack failed', err)
      isInternalNavigation = false
      // No history to go back to — fall back to the video source page if any.
      if (videoBackTarget.value) router.push(videoBackTarget.value)
      return
    }
    if (route.fullPath !== pathBefore) {
      forwardDepth.value++
    } else {
      // No history to go back to (e.g. deep-linked/refreshed page).
      isInternalNavigation = false
      // For a video page with a recorded source, jump there as a fallback.
      if (isVideoPage.value && videoBackTarget.value) {
        router.push(videoBackTarget.value)
      }
    }
  }

  async function goForward() {
    if (forwardDepth.value <= 0) return
    isInternalNavigation = true
    const pathBefore = route.fullPath
    try {
      await router.forward()
    } catch (err) {
      Logger.warn('[useNavigationHistory] goForward failed', err)
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

  // Unified label for the global back button: on video pages show the source
  // page name (e.g. "返回未读视频"); elsewhere just "返回".
  const backLabel = computed(() => {
    if (isVideoPage.value) return videoBackLabel.value
    return '返回'
  })

  const videoBackTarget = computed((): RouteLocationRaw | null => {
    const ctx = lastNonVideoRoute.value
    if (!ctx) return null
    return ctx.fullPath
  })

  const isVideoPage = computed(() => route.name === 'VideoPlay')

  // The global back button shows whenever there is somewhere to go back to:
  // either browser history exists (path !== initial) or an internal handler
  // is registered. On a video page we also accept having a recorded source.
  const showBackButton = computed(() => {
    if (canGoBack.value) return true
    if (isVideoPage.value && videoBackTarget.value) return true
    return false
  })

  function registerInternalBackHandler(handler: () => boolean) {
    internalBackHandler = handler
    return () => {
      if (internalBackHandler === handler) {
        internalBackHandler = null
        internalBackAvailable.value = false
      }
    }
  }

  function setInternalBackAvailable(available: boolean) {
    internalBackAvailable.value = available
  }

  return {
    canGoBack,
    canGoForward,
    goBack,
    goForward,
    backLabel,
    showBackButton,
    videoBackLabel,
    videoBackTarget,
    isVideoPage,
    lastNonVideoRoute,
    registerInternalBackHandler,
    setInternalBackAvailable,
  }
}

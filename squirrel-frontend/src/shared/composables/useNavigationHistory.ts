import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { findNavigationItemByKey } from '@/shared/constants/sidebar'
import type { AppNavKey } from '@/shared/constants/sidebar'

interface RouteSnapshot {
  fullPath: string
  name: string
  navKey: string
  sectionLabel: string
  pageTitle: string
}

// ── singleton state (shared across all composable instances) ──
const lastNonVideoRoute = ref<RouteSnapshot | null>(null)
const internalBackAvailable = ref(false)
let internalBackHandler: (() => boolean) | null = null
const hasInternalBack = computed(() => internalBackAvailable.value)

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

  const canGoBack = computed(() => (
    internalBackAvailable.value
    || Boolean(route.meta?.backTarget)
    || (isVideoPage.value && Boolean(videoBackTarget.value))
  ))

  async function goBack() {
    if (internalBackAvailable.value && internalBackHandler?.()) {
      return
    }

    if (isVideoPage.value && videoBackTarget.value) {
      await router.push(videoBackTarget.value)
      return
    }

    const target = route.meta?.backTarget as RouteLocationRaw | undefined
    if (target) {
      await router.push(target)
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

      // Record the page the user came from when entering a video page.
      // Video-to-video navigation (via replace) should not overwrite the original source.
      if (current.name === 'VideoPlay' && previous.name !== 'VideoPlay') {
        lastNonVideoRoute.value = captureRouteSnapshot(previous)
      }
    },
  )

  // Video page back-navigation context: the page the user came from when
  // entering VideoPlay. Used by VideoPlay's in-page back button and by
  // goBack() fallback when browser history is unavailable.
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
    goBack,
    hasInternalBack,
    videoBackLabel,
    videoBackTarget,
    isVideoPage,
    lastNonVideoRoute,
    registerInternalBackHandler,
    setInternalBackAvailable,
  }
}

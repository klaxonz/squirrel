<template>
  <div class="flex flex-col h-screen overflow-hidden bg-background">
    <!-- 1. Desktop Title Bar (Fixed Height) -->
    <DesktopTitleBar v-if="isDesktop" class="shrink-0 z-[100]" />

    <div class="flex flex-1 min-h-0 overflow-hidden">
      <!-- 2. Sidebar (Fixed Width, Full Height) -->
      <AppSidebar class="w-[var(--sidebar-width)] shrink-0 border-r border-border/40 z-50" />

      <!-- 3. Main Container -->
      <main class="flex-1 min-w-0 flex flex-col relative">
        <!-- 4. App Header (Fixed Height) -->
        <AppHeader class="shrink-0 z-40" />
        
        <!-- 5. Scrollable Content Area -->
        <div
          ref="mainScrollRef"
          class="flex-1 overflow-y-auto overflow-x-hidden relative scrollbar overflow-anchor-none"
          :class="musicBarPadding"
          :id="MAIN_SCROLL_ID"
        >
          <GlobalVideoPlayerHost />
          <slot />
        </div>
      </main>
    </div>

    <!-- Global Music Player Bar -->
    <GlobalMusicPlayerBar />

    <!-- Global toast stack (bottom-right, shared by all pages) -->
    <ToastProvider />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import DesktopTitleBar from '@/app/shell/DesktopTitleBar.vue'
import AppSidebar from '@/app/shell/AppSidebar.vue'
import AppHeader from '@/app/shell/AppHeader.vue'
import GlobalVideoPlayerHost from '@/features/playback/components/video-player/GlobalVideoPlayerHost.vue'
import GlobalMusicPlayerBar from '@/features/music/components/GlobalMusicPlayerBar.vue'
import ToastProvider from '@/shared/components/toast/ToastProvider.vue'
import { useThemeStore } from '@/shared/stores/theme'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { MAIN_SCROLL_ID } from '@/shared/composables/useMainScrollRoot'

type ScrollRouteState = {
  fullPath: string
  keepAlive: boolean
}

const scrollPositions = new Map<string, number>()
const isDesktop = window.desktopApp?.isDesktop === true
const themeStore = useThemeStore()
const musicPlayerStore = useMusicPlayerStore()
const nav = useNavigationHistory()
const route = useRoute()

const hasActiveMusicBar = computed(() =>
  Boolean(musicPlayerStore.currentTrack && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc))
)

const musicBarPadding = computed(() =>
  route.name === 'Music' && hasActiveMusicBar.value ? 'pb-20' : ''
)
const mainScrollRef = ref<HTMLElement | null>(null)
let activeScrollRoute: ScrollRouteState = {
  fullPath: route.fullPath,
  keepAlive: route.meta.keepAlive === true,
}
let previousHistoryPosition = Number(window.history.state?.position ?? 0)

const getScrollRouteState = (): ScrollRouteState => ({
  fullPath: route.fullPath,
  keepAlive: route.meta.keepAlive === true,
})

const restoreScrollForRoute = async (scrollRoute: ScrollRouteState, restoreSavedPosition: boolean) => {
  await nextTick()
  // Wait for the page-level crossfade Transition to finish so the new
  // page has settled its layout height before we restore scrollTop.
  await new Promise((resolve) => setTimeout(resolve, 200))
  const scrollEl = mainScrollRef.value
  if (!scrollEl) return

  scrollEl.scrollTop = restoreSavedPosition
    ? scrollPositions.get(scrollRoute.fullPath) ?? 0
    : 0
}

watch(() => route.fullPath, async () => {
  const currentHistoryPosition = Number(window.history.state?.position ?? previousHistoryPosition)
  const scrollEl = mainScrollRef.value
  // Save scroll position for ALL pages (not just keep-alive) so back-navigation
  // restores where the user left off regardless of caching.
  if (scrollEl) {
    scrollPositions.set(activeScrollRoute.fullPath, scrollEl.scrollTop)
  }

  activeScrollRoute = getScrollRouteState()
  await restoreScrollForRoute(activeScrollRoute, currentHistoryPosition < previousHistoryPosition)
  previousHistoryPosition = currentHistoryPosition
})

function handleKeydown(e: KeyboardEvent) {
  if (e.altKey && e.key === 'ArrowLeft') {
    e.preventDefault()
    nav.goBack()
  } else if (e.altKey && e.key === 'ArrowRight') {
    e.preventDefault()
    nav.goForward()
  }
}

onMounted(() => {
  themeStore.init()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
/* No extra styles needed, relying on Tailwind's utility classes */
</style>

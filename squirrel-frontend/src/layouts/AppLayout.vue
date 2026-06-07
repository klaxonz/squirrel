<template>
  <div class="flex flex-col h-screen overflow-hidden bg-background">
    <!-- 1. Desktop Title Bar (Fixed Height) -->
    <DesktopTitleBar v-if="isDesktop" class="shrink-0 z-[100]" />

    <div class="flex flex-1 min-h-0 overflow-hidden">
      <!-- 2. Sidebar (Fixed Width, Full Height) -->
      <AppSidebar 
        v-if="!isMobile" 
        class="w-[var(--sidebar-width)] shrink-0 border-r border-border/40 z-50" 
      />

      <!-- 3. Main Container -->
      <main class="flex-1 min-w-0 flex flex-col relative">
        <!-- 4. App Header (Fixed Height) -->
        <AppHeader class="shrink-0 z-40" />
        
        <!-- 5. Scrollable Content Area -->
        <div
          ref="mainScrollRef"
          class="flex-1 overflow-y-auto overflow-x-hidden relative scrollbar overflow-anchor-none"
          :class="musicBarPadding"
          id="app-main-scroll"
        >
          <GlobalVideoPlayerHost />
          <slot />
          
          <!-- Mobile Nav Spacer -->
          <div v-if="isMobile" class="h-nav shrink-0" />
        </div>
      </main>

      <!-- Mobile Navigation (Fixed at bottom) -->
      <MobileNavigation v-if="isMobile" class="fixed bottom-0 left-0 right-0 z-50 h-nav" />
    </div>

    <!-- Global Music Player Bar -->
    <GlobalMusicPlayerBar />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import DesktopTitleBar from '@/components/shell/DesktopTitleBar.vue'
import AppSidebar from '@/components/shell/AppSidebar.vue'
import AppHeader from '@/components/shell/AppHeader.vue'
import MobileNavigation from '@/components/shell/MobileNavigation.vue'
import GlobalVideoPlayerHost from '@/components/video-player/GlobalVideoPlayerHost.vue'
import GlobalMusicPlayerBar from '@/components/music/GlobalMusicPlayerBar.vue'
import { isMobile } from '@/composables/useMobile'
import { useThemeStore } from '@/stores/theme'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import { useNavigationHistory } from '@/composables/useNavigationHistory'

type ScrollRouteState = {
  fullPath: string
  keepAlive: boolean
}

const scrollPositions = new Map<string, number>()
const isDesktop = (window as any).desktopApp?.isDesktop === true
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
  const scrollEl = mainScrollRef.value
  if (!scrollEl) return

  scrollEl.scrollTop = scrollRoute.keepAlive && restoreSavedPosition
    ? scrollPositions.get(scrollRoute.fullPath) ?? 0
    : 0
}

watch(() => route.fullPath, async () => {
  const currentHistoryPosition = Number(window.history.state?.position ?? previousHistoryPosition)
  const scrollEl = mainScrollRef.value
  if (scrollEl && activeScrollRoute.keepAlive) {
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

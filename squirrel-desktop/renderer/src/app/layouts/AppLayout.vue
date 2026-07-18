<template>
  <div
    class="app-layout"
    :class="{
      'app-layout--desktop': isDesktop,
      'app-layout--immersive': isImmersiveSurface,
    }"
    :style="{ '--workspace-offset': sidebarWidth }"
  >
    <DesktopTitleBar
      v-if="isDesktop"
      class="app-layout__titlebar"
      :persist-sidebar-toggle="persistSidebarToggle"
    />

    <div class="app-layout__frame">
      <AppSidebar
        class="app-layout__sidebar"
        :collapsed="!isSidebarOpen"
      />

      <main class="app-layout__workspace">
        <AppHeader
          v-if="showAppHeader"
          class="app-layout__header"
          :persist-sidebar-toggle="persistSidebarToggle"
        />

        <div
          ref="mainScrollRef"
          class="app-layout__scroll custom-scrollbar overflow-anchor-none"
          :class="musicBarPadding"
          :id="MAIN_SCROLL_ID"
          @scroll.passive="handleScroll"
        >
          <GlobalVideoPlayerHost />
          <section class="app-layout__stage">
            <slot />
          </section>
        </div>
      </main>
    </div>

    <GlobalMusicPlayerBar />
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
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useThemeStore } from '@/shared/stores/theme'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { useUIStore } from '@/shared/stores/ui'
import { MAIN_SCROLL_ID } from '@/shared/composables/useMainScrollRoot'
import { useModalEscapeApi } from '@/shared/composables/useModalEscape'

const { isDesktop: isDesktopClient } = useDesktopBridge()
const isDesktop = isDesktopClient()
const themeStore = useThemeStore()
const musicPlayerStore = useMusicPlayerStore()
const uiStore = useUIStore()
const nav = useNavigationHistory()
const route = useRoute()
const modalApi = useModalEscapeApi()

const isSidebarOpen = computed(() => uiStore.isSidebarOpen)

/** Route meta.sidebar drives immersive surfaces (playback / RSS / music). */
type SidebarRouteMeta = { mode?: string; defaultOpen?: boolean }

const sidebarRouteMeta = computed(() => {
  const raw = route.meta.sidebar
  if (!raw || typeof raw !== 'object') return null
  return raw as SidebarRouteMeta
})

const isImmersiveSurface = computed(() =>
  Boolean(sidebarRouteMeta.value && sidebarRouteMeta.value.defaultOpen === false),
)
const persistSidebarToggle = computed(() => !isImmersiveSurface.value)
const sidebarWidth = computed(() => (
  isSidebarOpen.value ? 'var(--sidebar-expanded-width)' : 'var(--sidebar-collapsed-width)'
))

/**
 * Every ordinary authenticated surface keeps the same 44px desktop header and
 * account entry. Routes without a search task render the header's balanced
 * spacer; only the video watch surface deliberately gives the player that row.
 */
const showAppHeader = computed(() => !isDesktop && route.name !== 'VideoPlay')

const hasActiveMusicBar = computed(() =>
  Boolean(
    musicPlayerStore.currentTrack
    && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc || musicPlayerStore.error),
  )
)

const musicBarPadding = computed(() =>
  route.name === 'Music' && hasActiveMusicBar.value ? 'app-layout__scroll--music-player' : ''
)

// Immersive host routes (playback / RSS / music) collapse the global app rail
// without writing localStorage, then restore the user preference on exit.
watch(
  () => sidebarRouteMeta.value?.defaultOpen,
  (defaultOpen, previous) => {
    if (typeof defaultOpen === 'boolean') {
      uiStore.setSidebarOpen(defaultOpen, { persist: false })
      return
    }
    if (typeof previous === 'boolean') {
      uiStore.restorePersistedSidebarOpen()
    }
  },
  { immediate: true },
)

const mainScrollRef = ref<HTMLElement | null>(null)
let scrollSaveTimer: ReturnType<typeof setTimeout> | null = null
let detachDesktopNavListener: (() => void) | null = null

function handleScroll() {
  const scrollEl = mainScrollRef.value
  if (!scrollEl) return
  if (scrollSaveTimer) clearTimeout(scrollSaveTimer)
  scrollSaveTimer = setTimeout(() => {
    nav.saveScrollPosition(scrollEl.scrollTop)
  }, 120)
}

watch(() => route.fullPath, async () => {
  await nextTick()
  const scrollEl = mainScrollRef.value
  if (!scrollEl) return
  // 用 entry 里记录的 scrollY 恢复滚动位置 —— 取代旧的 "按 history.position
  // 比较前后大小估算" 的脆弱方案。
  const saved = nav.current.value?.scrollY ?? 0
  scrollEl.scrollTop = saved
})

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  return target.isContentEditable
}

function handleKeydown(e: KeyboardEvent) {
  if (isEditableTarget(e.target)) return
  const mod = e.metaKey || e.ctrlKey
  if (mod && (e.key === 'b' || e.key === 'B')) {
    e.preventDefault()
    uiStore.toggleSidebar({ persist: persistSidebarToggle.value })
    return
  }
  // Back: Alt+← (cross-platform) or Cmd/Ctrl+[ (macOS-standard)
  if ((e.altKey && e.key === 'ArrowLeft') || (mod && e.key === '[')) {
    if (nav.canGoBack.value) {
      e.preventDefault()
      void nav.goBack()
    }
    return
  }
  // Forward: Alt+→ or Cmd/Ctrl+]
  if ((e.altKey && e.key === 'ArrowRight') || (mod && e.key === ']')) {
    if (nav.canGoForward.value) {
      e.preventDefault()
      void nav.goForward()
    }
    return
  }
  // Esc: modal stack first; only then goBack on bare body/main/div focus.
  if (e.key === 'Escape' && !modalApi.hasOpen() && nav.canGoBack.value) {
    const tag = (e.target as HTMLElement | null)?.tagName
    if (tag === 'BODY' || tag === 'MAIN' || tag === 'DIV') {
      e.preventDefault()
      void nav.goBack()
    }
  }
}

onMounted(() => {
  themeStore.init()
  window.addEventListener('keydown', handleKeydown)

  // Electron 鼠标侧键 / `app-command: browser-backward|forward` 在
  // window.mjs 里 forward 给渲染进程的 `desktop:navigate` 事件。
  const bridge = (window as unknown as { desktopApp?: {
    onNavigate?: (cb: (direction: 'back' | 'forward') => void) => () => void
  } }).desktopApp
  if (bridge?.onNavigate) {
    detachDesktopNavListener = bridge.onNavigate((direction) => {
      if (direction === 'back' && nav.canGoBack.value) {
        void nav.goBack()
      } else if (direction === 'forward' && nav.canGoForward.value) {
        void nav.goForward()
      }
    })
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (scrollSaveTimer) clearTimeout(scrollSaveTimer)
  detachDesktopNavListener?.()
  detachDesktopNavListener = null
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: hsl(var(--foreground));
  background: hsl(var(--background));
}

.app-layout__titlebar {
  flex: 0 0 auto;
  position: relative;
  z-index: var(--z-sidebar);
}

.app-layout__frame {
  flex: 1 1 auto;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.app-layout__sidebar {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--workspace-offset);
  overflow: hidden;
  z-index: 1;
  transition: width var(--duration-base) var(--ease-out);
}

.app-layout__workspace {
  position: absolute;
  inset: 0 0 0 var(--workspace-offset);
  z-index: var(--z-sidebar);
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: hsl(var(--background));
  transition: left var(--duration-base) var(--ease-out);
  will-change: left;
}

.app-layout__header {
  flex: 0 0 auto;
}

.app-layout__scroll {
  flex: 1 1 auto;
  min-height: 0;
  position: relative;
  overflow-x: hidden;
  overflow-y: auto;
  scroll-behavior: auto;
}

.app-layout__scroll--music-player {
  padding-bottom: var(--app-music-player-height);
}

/*
  Stage is a fixed-height flex host equal to the scrollport. Document-style
  pages (fill=false) still outer-scroll because their content overflows the
  stage box. Workbench pages (AppPageShell fill) consume the full host and
  own their own scroll regions — see :has(.app-page-shell--fill) below.
*/
.app-layout__stage {
  position: relative;
  display: flex;
  height: 100%;
  min-height: 100%;
  flex-direction: column;
}

/*
  Contained workbench (订阅 / 歌单 / 设置 / 音乐 / RSS …): lock the outer
  scrollport so only the workbench header stays pinned and
  .app-workbench__scroll / sidebar lists move. Without this, percentage
  height on fill pages fails against a min-height-only ancestor and the
  entire workspace scrolls as one document.
*/
.app-layout__scroll:has(:deep(.app-page-shell--fill)) {
  display: flex;
  flex-direction: column;
  overflow-y: hidden;
}

.app-layout__scroll:has(:deep(.app-page-shell--fill)) .app-layout__stage {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

@media (prefers-reduced-motion: reduce) {
  .app-layout__workspace {
    transition: none;
  }
}

</style>

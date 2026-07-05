<template>
  <div
    class="app-layout"
    :class="{ 'app-layout--desktop': isDesktop }"
    :style="{ '--sidebar-width': isSidebarOpen ? 'var(--sidebar-expanded-width)' : 'var(--sidebar-collapsed-width)' }"
  >
    <DesktopTitleBar v-if="isDesktop" class="app-layout__titlebar" />

    <div class="app-layout__frame">
      <AppSidebar class="app-layout__sidebar" />

      <main class="app-layout__workspace">
        <AppHeader class="app-layout__header" />

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

const { isDesktop: isDesktopClient } = useDesktopBridge()
const isDesktop = isDesktopClient()
const themeStore = useThemeStore()
const musicPlayerStore = useMusicPlayerStore()
const uiStore = useUIStore()
const nav = useNavigationHistory()
const route = useRoute()

const isSidebarOpen = computed(() => uiStore.isSidebarOpen)

const hasActiveMusicBar = computed(() =>
  Boolean(musicPlayerStore.currentTrack && (musicPlayerStore.resolvingUrl || musicPlayerStore.audioSrc))
)

const musicBarPadding = computed(() =>
  route.name === 'Music' && hasActiveMusicBar.value ? 'pb-20' : ''
)

const mainScrollRef = ref<HTMLElement | null>(null)
let scrollSaveTimer: ReturnType<typeof setTimeout> | null = null
let detachIpcListener: (() => void) | null = null
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
  // Esc: pop detail page if applicable
  if (e.key === 'Escape' && nav.canGoBack.value) {
    // Only intercept Esc on detail-like pages; let inner dialogs dismiss first.
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
  detachIpcListener?.()
  detachDesktopNavListener?.()
  detachIpcListener = null
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
  background:
    radial-gradient(900px 420px at 58% -180px, hsl(var(--primary) / 0.07), transparent 64%),
    linear-gradient(180deg, hsl(var(--background)), hsl(var(--background)));
}

.app-layout__titlebar {
  flex: 0 0 auto;
  position: relative;
  z-index: var(--z-sidebar);
}

.app-layout__frame {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4) var(--space-4);
  overflow: hidden;
}

.app-layout--desktop .app-layout__frame {
  padding-top: var(--space-3);
}

.app-layout__sidebar {
  flex: 0 0 var(--sidebar-width);
  position: relative;
  z-index: var(--z-sidebar);
}

.app-layout__workspace {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: calc(var(--radius-xl) + 4px);
  background: hsl(var(--background) / 0.72);
  box-shadow:
    0 1px 0 hsl(var(--foreground) / 0.04) inset,
    0 18px 44px hsl(0 0% 0% / 0.18);
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

.app-layout__stage {
  min-height: 100%;
}

@media (prefers-reduced-motion: reduce) {
  .app-layout__workspace {
    box-shadow: 0 1px 0 hsl(var(--foreground) / 0.04) inset;
  }
}
</style>

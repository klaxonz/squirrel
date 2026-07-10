<template>
  <header class="titlebar">
    <div class="titlebar__navigation no-drag">
      <Button
        type="button"
        variant="ghost"
        size="mini-icon"
        class="titlebar__navigation-button"
        :title="isSidebarOpen ? '收起侧边栏 (Ctrl+B)' : '展开侧边栏 (Ctrl+B)'"
        :aria-label="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
        :aria-expanded="isSidebarOpen"
        @click="uiStore.toggleSidebar()"
      >
        <AppIcon :name="isSidebarOpen ? 'panelClose' : 'panelOpen'" class="titlebar__navigation-icon" />
      </Button>

      <span class="titlebar__navigation-divider" aria-hidden="true" />

      <Button
        type="button"
        variant="ghost"
        size="mini-icon"
        class="titlebar__navigation-button"
        title="后退"
        aria-label="后退"
        :disabled="!canGoBack"
        @click="goBack"
      >
        <AppIcon name="chevronLeft" class="titlebar__navigation-icon" />
      </Button>

      <Button
        type="button"
        variant="ghost"
        size="mini-icon"
        class="titlebar__navigation-button"
        title="前进"
        aria-label="前进"
        :disabled="!canGoForward"
        @click="goForward"
      >
        <AppIcon name="chevronRight" class="titlebar__navigation-icon" />
      </Button>
    </div>

    <div class="titlebar__drag" aria-hidden="true" />

    <div class="titlebar__controls no-drag">
      <Button
        v-for="btn in controls"
        :key="btn.label"
        type="button"
        variant="ghost"
        size="mini-icon"
        class="titlebar__control"
        :class="{ 'titlebar__control--close': btn.type === 'close' }"
        :title="btn.label"
        :aria-label="btn.label"
        @click="btn.action"
      >
        <AppIcon :name="btn.icon" class="titlebar__control-icon" />
      </Button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { useUIStore } from '@/shared/stores/ui'

const desktop = window.desktopApp
const nav = useNavigationHistory()
const uiStore = useUIStore()
const isMaximized = ref(false)
let removeWindowStateListener: (() => void) | undefined

const isSidebarOpen = computed(() => uiStore.isSidebarOpen)
const canGoBack = computed(() => nav.canGoBack.value)
const canGoForward = computed(() => nav.canGoForward.value)

const controls = computed(() => ([
  { icon: 'minimizeWindow' as AppIconName, action: () => { desktop?.minimizeWindow?.() }, label: '最小化' },
  { icon: (isMaximized.value ? 'restoreWindow' : 'maximizeWindow') as AppIconName, action: toggleMaximize, label: isMaximized.value ? '还原' : '最大化' },
  { icon: 'close' as AppIconName, action: () => { desktop?.closeWindow?.() }, label: '关闭', type: 'close' as const },
]))

async function toggleMaximize() {
  const state = await desktop?.toggleMaximizeWindow?.()
  isMaximized.value = state?.isMaximized === true
}

function goBack() {
  void nav.goBack()
}

function goForward() {
  void nav.goForward()
}

onMounted(async () => {
  if (desktop?.getWindowState) {
    const state = await desktop.getWindowState()
    isMaximized.value = state?.isMaximized === true
  }
  removeWindowStateListener = desktop?.onWindowStateChange?.((state: DesktopWindowState) => {
    isMaximized.value = state?.isMaximized === true
  })
})

onUnmounted(() => {
  removeWindowStateListener?.()
})
</script>

<style scoped>
.titlebar {
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0;
  /* Same canvas as the shell — no floating title strip. */
  background: hsl(var(--background));
  border-bottom: 1px solid var(--app-hairline);
  user-select: none;
  -webkit-app-region: drag;
}

.titlebar__navigation {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  height: 100%;
  padding: 0 0.25rem;
  flex: 0 0 auto;
  -webkit-app-region: no-drag;
}

.titlebar__navigation-button {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
}

.titlebar__navigation-button:hover:not(:disabled) {
  background: hsl(var(--foreground) / 0.065);
  color: hsl(var(--foreground));
}

.titlebar__navigation-button:disabled {
  opacity: 0.32;
}

.titlebar__navigation-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.titlebar__navigation-divider {
  width: 1px;
  height: 0.875rem;
  margin: 0 0.125rem;
  background: var(--app-hairline);
}

.titlebar__drag {
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
}

.titlebar__controls {
  display: inline-flex;
  align-items: center;
  gap: 0;
  flex: 0 0 auto;
  -webkit-app-region: no-drag;
}

.titlebar__control {
  width: 2.5rem;
  height: 2rem;
  color: hsl(var(--muted-foreground));
  border-radius: 0;
}
.titlebar__control:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}
.titlebar__control--close:hover {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}
.titlebar__control-icon {
  width: 0.875rem;
  height: 0.875rem;
}

@media (prefers-reduced-motion: reduce) {
  .titlebar__navigation-button,
  .titlebar__control {
    transition: none;
  }
}
</style>

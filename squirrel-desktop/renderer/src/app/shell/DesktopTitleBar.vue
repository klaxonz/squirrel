<template>
  <header class="titlebar">
    <!--
      Full-bleed top chrome. Brand lives in the sidebar active state only —
      no second logo here (avoids dual brand anchors in the top-left).
    -->
    <div class="titlebar__nav no-drag">
      <Button
        type="button"
        text
        variant="secondary"
        size="sm"
        icon-only
        class="titlebar__icon-btn"
        :title="isSidebarOpen ? '收起侧边栏 (Ctrl+B)' : '展开侧边栏 (Ctrl+B)'"
        :aria-label="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
        :aria-expanded="isSidebarOpen"
        @click="toggleSidebar"
      >
        <AppIcon name="panelLeft" class="titlebar__icon" />
      </Button>

      <Button
        type="button"
        text
        variant="secondary"
        size="sm"
        icon-only
        class="titlebar__icon-btn"
        title="后退"
        aria-label="后退"
        :disabled="!canGoBack"
        @click="goBack"
      >
        <AppIcon name="chevronLeft" class="titlebar__icon" />
      </Button>

      <Button
        type="button"
        text
        variant="secondary"
        size="sm"
        icon-only
        class="titlebar__icon-btn"
        title="前进"
        aria-label="前进"
        :disabled="!canGoForward"
        @click="goForward"
      >
        <AppIcon name="chevronRight" class="titlebar__icon" />
      </Button>
    </div>

    <AppHeader
      class="titlebar__command no-drag"
      variant="desktop"
    />

    <div class="titlebar__window no-drag">
      <Button
        v-for="btn in controls"
        :key="btn.label"
        type="button"
        text
        variant="secondary"
        size="sm"
        icon-only
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
import AppHeader from '@/app/shell/AppHeader.vue'
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'
import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'
import { useUIStore } from '@/shared/stores/ui'

const props = withDefaults(defineProps<{
  persistSidebarToggle?: boolean
}>(), {
  persistSidebarToggle: true,
})

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

function toggleSidebar() {
  uiStore.toggleSidebar({ persist: props.persistSidebarToggle })
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
/*
  [ ≡ ‹ › ] [ ===== search ===== ] [ user ] [ window ]
  Brand mark lives only in the sidebar active language — not here.
*/
.titlebar {
  height: var(--app-titlebar-height);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-left: 0.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.9);
  background: hsl(var(--card));
  user-select: none;
  -webkit-app-region: drag;
  app-region: drag;
}

.titlebar__nav {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.15rem;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.titlebar__icon-btn {
  width: 1.8rem;
  height: 1.8rem;
  border-radius: 999px;
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.titlebar__icon-btn:hover:not(:disabled) {
  background: var(--app-control-hover-bg);
  color: hsl(var(--foreground));
}

.titlebar__icon-btn:disabled {
  opacity: 0.28;
}

.titlebar__icon {
  width: 0.875rem;
  height: 0.875rem;
}

.titlebar__command {
  flex: 1 1 auto;
  min-width: 0;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.titlebar__window {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.titlebar__control {
  width: 2.75rem;
  height: var(--app-titlebar-height);
  border-radius: 0;
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.titlebar__control:hover {
  background: var(--app-control-hover-bg);
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
  .titlebar__icon-btn,
  .titlebar__control {
    transition: none;
  }
}
</style>

<template>
  <header class="titlebar">
    <!--
      Full-bleed top chrome. The brand lives here in desktop; the sidebar
      starts below with navigation only (no duplicate brand row).
    -->
    <div class="titlebar__brand no-drag">
      <RouterLink to="/home" class="titlebar__brand-link" aria-label="归仓">
        <BrandMark class="titlebar__brand-mark" />
        <span class="titlebar__brand-name">归仓</span>
      </RouterLink>
    </div>

    <div class="titlebar__nav no-drag">
      <Button
        type="button"
       
        variant="ghost"
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
       
        variant="ghost"
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
       
        variant="ghost"
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
       
        variant="ghost"
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
import { RouterLink } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppHeader from '@/app/shell/AppHeader.vue'
import BrandMark from '@/shared/components/BrandMark.vue'
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
/* Compact command row: brand, navigation, search, account, and window actions. */
.titlebar {
  height: var(--app-titlebar-height);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding-left: 0;
  border-bottom: 1px solid hsl(var(--border));
  background: hsl(var(--background));
  user-select: none;
  -webkit-app-region: drag;
  app-region: drag;
}

.titlebar__brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  height: 100%;
  padding: 0 0.5rem 0 0.75rem;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.titlebar__brand-link {
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.5rem;
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  text-decoration: none;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.titlebar__brand-link:hover {
  background: var(--app-control-hover-bg);
}

.titlebar__brand-mark {
  width: 1.25rem;
  height: 1.25rem;
  flex: 0 0 auto;
  color: hsl(var(--brand));
}

.titlebar__brand-name {
  font-family: var(--font-display);
  font-size: var(--app-text-xl);
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1;
  white-space: nowrap;
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
  width: 2rem;
  height: 2rem;
  border-radius: var(--app-control-item-radius);
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
  -webkit-app-region: drag;
  app-region: drag;
}

.titlebar__window {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.125rem;
  margin-left: 0.25rem;
  padding-right: 0.5rem;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.titlebar__control {
  width: 2.5rem;
  height: 2rem;
  border: 0;
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.titlebar__control:hover {
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground));
}

.titlebar__control:active {
  background: hsl(var(--foreground) / 0.09);
}

.titlebar__control:focus-visible {
  outline: 2px solid hsl(var(--ring) / 0.6);
  outline-offset: -2px;
}

.titlebar__control--close:hover {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}

.titlebar__control--close:active {
  background: hsl(var(--destructive) / 0.9);
  color: hsl(var(--destructive-foreground));
}

.titlebar__control-icon {
  width: 0.875rem;
  height: 0.875rem;
}

@media (max-width: 1180px) {
  .titlebar__brand {
    padding: 0 0.35rem 0 0.5rem;
  }

  .titlebar__brand-name {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .titlebar__icon-btn,
  .titlebar__control,
  .titlebar__brand-link {
    transition: none;
  }
}
</style>

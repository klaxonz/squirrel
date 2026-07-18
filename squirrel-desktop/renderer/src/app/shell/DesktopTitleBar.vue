<template>
  <header class="titlebar">
    <div class="titlebar__brand" :class="{ 'is-collapsed': !isSidebarOpen }" aria-label="归仓">
      <BrandMark class="titlebar__brand-mark" />
      <span class="titlebar__brand-copy">
        <strong>归仓</strong>
      </span>
    </div>
    <div class="titlebar__navigation no-drag">
      <Button
        type="button"
        text severity="secondary"
        size="sm"
        icon-only
        class="titlebar__navigation-button"
        :title="isSidebarOpen ? '收起侧边栏 (Ctrl+B)' : '展开侧边栏 (Ctrl+B)'"
        :aria-label="isSidebarOpen ? '收起侧边栏' : '展开侧边栏'"
        :aria-expanded="isSidebarOpen"
        @click="uiStore.toggleSidebar()"
      >
        <AppIcon name="panelLeft" class="titlebar__navigation-icon" />
      </Button>

      <Button
        type="button"
        text severity="secondary"
        size="sm"
        icon-only
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
        text severity="secondary"
        size="sm"
        icon-only
        class="titlebar__navigation-button"
        title="前进"
        aria-label="前进"
        :disabled="!canGoForward"
        @click="goForward"
      >
        <AppIcon name="chevronRight" class="titlebar__navigation-icon" />
      </Button>
    </div>

    <AppHeader class="titlebar__command no-drag" />

    <div class="titlebar__controls no-drag">
      <Button
        v-for="btn in controls"
        :key="btn.label"
        type="button"
        text severity="secondary"
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
import BrandMark from '@/shared/components/BrandMark.vue'
import AppHeader from '@/app/shell/AppHeader.vue'
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
  height: var(--app-titlebar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0;
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--background));
  user-select: none;
  -webkit-app-region: drag;
}

.titlebar__brand {
  display: inline-flex;
  width: var(--workspace-offset);
  height: 100%;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.625rem;
  overflow: hidden;
  border-right: 1px solid var(--app-hairline);
  padding-inline: 0.875rem;
  color: hsl(var(--foreground));
  transition: width var(--duration-base) var(--ease-out);
}

.titlebar__brand.is-collapsed {
  justify-content: center;
  padding-inline: 0;
}

.titlebar__brand-mark {
  width: 1.5rem;
  height: 1.5rem;
  flex: 0 0 auto;
  color: hsl(var(--primary));
}

.titlebar__brand-copy {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  white-space: nowrap;
}

.titlebar__brand-copy strong {
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 680;
  letter-spacing: -0.02em;
}

.titlebar__brand.is-collapsed .titlebar__brand-copy {
  display: none;
}

.titlebar__navigation {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  height: 100%;
  padding: 0 0.625rem;
  border-right: 1px solid var(--app-hairline);
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
  background: hsl(var(--accent) / 0.7);
  color: hsl(var(--foreground));
}

.titlebar__navigation-button:disabled {
  opacity: 0.32;
}

.titlebar__navigation-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.titlebar__command {
  flex: 1 1 auto;
  min-width: 0;
  -webkit-app-region: no-drag;
}

.titlebar__command:deep(.app-header) {
  height: var(--app-titlebar-height);
  grid-template-columns: minmax(1rem, 1fr) minmax(18rem, 34rem) auto;
  border-bottom: 0;
  padding: 0 0.75rem 0 1rem;
  background: hsl(var(--background));
}

.titlebar__command:deep(.app-header__leading) {
  min-width: 1rem;
}

.titlebar__command:deep(.app-header__user) {
  max-width: 9rem;
}

.titlebar__command:deep(.global-search__box) {
  height: 2rem;
  border: 1px solid hsl(var(--border) / 0.62);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.22);
  box-shadow: none;
}

.titlebar__command:deep(.global-search__box:focus-within) {
  border-color: hsl(var(--primary) / 0.55);
  background: hsl(var(--background));
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.1);
}

.titlebar__command:deep(.global-search__suggestions) {
  border-color: hsl(var(--border) / 0.7);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-popover);
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
  height: var(--app-titlebar-height);
  color: hsl(var(--muted-foreground));
  border-radius: 0;
}

.titlebar__control:hover {
  background: hsl(var(--accent) / 0.72);
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
  .titlebar__brand,
  .titlebar__navigation-button,
  .titlebar__control {
    transition: none;
  }
}
</style>

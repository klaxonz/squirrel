<template>
  <header class="titlebar">
    <div class="titlebar__lead no-drag">
      <button
        type="button"
        class="titlebar__brand"
        title="归仓"
        aria-label="归仓（首页）"
        @click="goHome"
      >
        <BrandLogo size="xs" />
        <span class="titlebar__brand-label">归仓</span>
      </button>
    </div>

    <div class="titlebar__controls no-drag">
      <button
        v-for="btn in controls"
        :key="btn.label"
        type="button"
        class="titlebar__control"
        :class="{ 'titlebar__control--close': btn.type === 'close' }"
        :title="btn.label"
        :aria-label="btn.label"
        @click="btn.action"
      >
        <AppIcon :name="btn.icon" class="titlebar__control-icon" />
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import BrandLogo from '@/shared/components/BrandLogo.vue'
import type { AppIconName } from '@/shared/icons/app-icons'

const router = useRouter()
const desktop = window.desktopApp
const isMaximized = ref(false)
let removeWindowStateListener: (() => void) | undefined

// UI-011: brand click must NOT replace the history stack — users expect to be
// able to Alt+← back to wherever they came from. push() preserves it.
const goHome = () => {
  if (router.currentRoute.value.fullPath === '/') return
  void router.push('/')
}

const controls = computed(() => ([
  { icon: 'minimizeWindow' as AppIconName, action: () => { desktop?.minimizeWindow?.() }, label: '最小化' },
  { icon: (isMaximized.value ? 'restoreWindow' : 'maximizeWindow') as AppIconName, action: toggleMaximize, label: isMaximized.value ? '还原' : '最大化' },
  { icon: 'close' as AppIconName, action: () => { desktop?.closeWindow?.() }, label: '关闭', type: 'close' as const },
]))

async function toggleMaximize() {
  const state = await desktop?.toggleMaximizeWindow?.()
  isMaximized.value = state?.isMaximized === true
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
  padding: 0 var(--space-4);
  background: hsl(var(--card) / 0.6);
  border-bottom: 1px solid var(--app-hairline);
  user-select: none;
}

.titlebar__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 1.75rem;
  padding: 0 var(--space-2) 0 0.375rem;
  border: 0;
  background: transparent;
  border-radius: var(--radius-md);
  color: hsl(var(--foreground));
  cursor: pointer;
  outline: none;
  transition: background-color var(--duration-fast) var(--ease-default);
}
.titlebar__brand:hover {
  background: hsl(var(--accent));
}
.titlebar__brand:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.4);
}
.titlebar__brand-label {
  font-family: var(--app-heading-font);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: -0.005em;
}

.titlebar__controls {
  display: inline-flex;
  align-items: center;
  gap: 0;
}

.titlebar__control {
  width: 2.5rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}
.titlebar__control:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}
.titlebar__control:focus-visible {
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.5);
}
.titlebar__control--close:hover {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}
.titlebar__control-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.drag {
  -webkit-app-region: drag;
}
.no-drag {
  -webkit-app-region: no-drag;
}

@media (prefers-reduced-motion: reduce) {
  .titlebar__brand,
  .titlebar__control {
    transition: none;
  }
}
</style>

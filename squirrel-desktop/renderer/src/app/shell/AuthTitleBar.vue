<template>
  <!-- Auth-only chrome: drag region + window controls. No nav / search / account. -->
  <header class="auth-titlebar" aria-label="窗口">
    <div class="auth-titlebar__drag" />
    <div class="auth-titlebar__controls">
      <Button
        v-for="btn in controls"
        :key="btn.label"
        type="button"
       
        variant="secondary"
        size="sm"
        icon-only
        class="auth-titlebar__control"
        :class="{ 'auth-titlebar__control--close': btn.type === 'close' }"
        :title="btn.label"
        :aria-label="btn.label"
        @click="btn.action"
      >
        <AppIcon :name="btn.icon" class="auth-titlebar__control-icon" />
      </Button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'

const desktop = window.desktopApp
const isMaximized = ref(false)
let removeWindowStateListener: (() => void) | undefined

const controls = computed(() => ([
  { icon: 'minimizeWindow' as AppIconName, action: () => { desktop?.minimizeWindow?.() }, label: '最小化' },
  {
    icon: (isMaximized.value ? 'restoreWindow' : 'maximizeWindow') as AppIconName,
    action: toggleMaximize,
    label: isMaximized.value ? '还原' : '最大化',
  },
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
.auth-titlebar {
  display: flex;
  height: var(--app-titlebar-height);
  flex: none;
  align-items: stretch;
  user-select: none;
  -webkit-app-region: drag;
  app-region: drag;
  background: transparent;
}

.auth-titlebar__drag {
  flex: 1 1 auto;
  min-width: 0;
  -webkit-app-region: drag;
  app-region: drag;
}

.auth-titlebar__controls {
  display: inline-flex;
  flex: none;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}

.auth-titlebar__control {
  width: 2.75rem;
  height: var(--app-titlebar-height);
  border-radius: 0;
  color: hsl(var(--muted-foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.auth-titlebar__control:hover {
  background: var(--app-control-hover-bg);
  color: hsl(var(--foreground));
}

.auth-titlebar__control--close:hover {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}

.auth-titlebar__control-icon {
  width: 0.875rem;
  height: 0.875rem;
}
</style>

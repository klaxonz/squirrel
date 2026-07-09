<template>
  <header class="titlebar">
    <!--
      Pure window chrome (VS Code / mature Electron): drag region + window
      controls. Product identity lives in the sidebar workspace header.
    -->
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

const desktop = window.desktopApp
const isMaximized = ref(false)
let removeWindowStateListener: (() => void) | undefined

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
  justify-content: flex-end;
  padding: 0;
  /* Same canvas as the shell — no floating title strip. */
  background: hsl(var(--background));
  border-bottom: 1px solid var(--app-hairline);
  user-select: none;
  -webkit-app-region: drag;
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
  .titlebar__control {
    transition: none;
  }
}
</style>

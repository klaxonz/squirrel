<template>
  <header class="h-8 flex items-center justify-between px-4 bg-background/95 backdrop-blur border-b border-border/50 select-none drag">
    <div class="flex items-center gap-2">
      <!-- Identity label removed for cleaner look -->
    </div>
    
    <div class="flex items-center no-drag">
      <button v-for="btn in controls" :key="btn.label" 
        @click="btn.action"
        class="w-10 h-8 flex items-center justify-center hover:bg-accent hover:text-foreground transition-colors group"
        :class="{ 'hover:bg-red-600 hover:text-white': btn.type === 'close' }"
      >
        <AppIcon :name="btn.icon" class="w-3.5 h-3.5" />
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { AppIconName } from '@/icons/app-icons'

const desktop = (window as any).desktopApp
const isMaximized = ref(false)

const controls = computed<Array<{
  icon: AppIconName
  action: () => Promise<void> | void
  label: string
  type?: 'close'
}>>(() => ([
  { icon: 'minimizeWindow', action: () => desktop?.minimizeWindow(), label: '最小化' },
  { icon: isMaximized.value ? 'restoreWindow' : 'maximizeWindow', action: toggleMaximize, label: '最大化' },
  { icon: 'close', action: () => desktop?.closeWindow(), label: '关闭', type: 'close' },
]))

async function toggleMaximize() {
  isMaximized.value = await desktop?.toggleMaximizeWindow()
}

onMounted(async () => {
  if (desktop?.getWindowState) {
    const state = await desktop.getWindowState()
    isMaximized.value = state.isMaximized
  }
})
</script>

<style scoped>
.drag {
  -webkit-app-region: drag;
}
.no-drag {
  -webkit-app-region: no-drag;
}
</style>

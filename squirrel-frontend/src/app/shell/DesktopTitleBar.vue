<template>
  <header class="h-8 flex items-center justify-between px-4 bg-background/95 backdrop-blur border-b border-border/50 select-none drag">
    <div class="flex items-center gap-2 no-drag">
      <router-link
        to="/"
        replace
        class="flex items-center gap-2 h-7 pl-1.5 pr-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/40 hover:bg-accent/50 transition-colors"
        title="归仓"
      >
        <BrandLogo size="xs" />
        <span class="text-xs font-semibold tracking-tight text-foreground font-display">归仓</span>
      </router-link>
    </div>
    
    <div class="flex items-center no-drag">
      <button v-for="btn in controls" :key="btn.label" 
        @click="btn.action"
        :title="btn.label"
        class="w-10 h-8 flex items-center justify-center hover:bg-accent hover:text-foreground transition-colors group"
        :class="{ 'hover:bg-destructive hover:text-destructive-foreground': btn.type === 'close' }"
      >
        <AppIcon :name="btn.icon" class="w-3.5 h-3.5" />
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import BrandLogo from '@/shared/components/BrandLogo.vue'
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
.drag {
  -webkit-app-region: drag;
}
.no-drag {
  -webkit-app-region: no-drag;
}
</style>

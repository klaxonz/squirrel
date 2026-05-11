<template>
  <div class="flex flex-col h-screen overflow-hidden bg-background">
    <!-- 1. Desktop Title Bar (Fixed Height) -->
    <DesktopTitleBar v-if="isDesktop" class="shrink-0 z-[100]" />

    <div class="flex flex-1 min-h-0 overflow-hidden">
      <!-- 2. Sidebar (Fixed Width, Full Height) -->
      <AppSidebar 
        v-if="!isMobile" 
        class="w-[var(--sidebar-width)] shrink-0 border-r border-border/40 z-50" 
      />

      <!-- 3. Main Container -->
      <main class="flex-1 min-w-0 flex flex-col relative">
        <!-- 4. App Header (Fixed Height) -->
        <AppHeader class="shrink-0 z-40" />
        
        <!-- 5. Scrollable Content Area -->
        <div class="flex-1 overflow-y-auto overflow-x-hidden relative scrollbar overflow-anchor-none" id="app-main-scroll">
          <GlobalVideoPlayerHost />
          <slot />
          
          <!-- Mobile Nav Spacer -->
          <div v-if="isMobile" class="h-nav shrink-0" />
        </div>
      </main>

      <!-- Mobile Navigation (Fixed at bottom) -->
      <MobileNavigation v-if="isMobile" class="fixed bottom-0 left-0 right-0 z-50 h-nav" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import DesktopTitleBar from '@/components/shell/DesktopTitleBar.vue'
import AppSidebar from '@/components/shell/AppSidebar.vue'
import AppHeader from '@/components/shell/AppHeader.vue'
import MobileNavigation from '@/components/shell/MobileNavigation.vue'
import GlobalVideoPlayerHost from '@/components/video-player/GlobalVideoPlayerHost.vue'
import { isMobile } from '@/composables/useMobile'
import { useThemeStore } from '@/stores/theme'

const isDesktop = (window as any).desktopApp?.isDesktop === true
const themeStore = useThemeStore()

onMounted(() => {
  themeStore.init()
})
</script>

<style scoped>
/* No extra styles needed, relying on Tailwind's utility classes */
</style>

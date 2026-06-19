<template>
  <div class="h-screen overflow-hidden flex flex-col bg-background">
    <DesktopTitleBar v-if="isDesktop" />
    <div class="flex-1 overflow-auto">
      <slot />
    </div>
    <ToastProvider />
  </div>
</template>

<script setup lang="ts">
import DesktopTitleBar from '@/app/shell/DesktopTitleBar.vue'
import ToastProvider from '@/shared/components/toast/ToastProvider.vue'

const isDesktop = window.desktopApp?.isDesktop === true
</script>

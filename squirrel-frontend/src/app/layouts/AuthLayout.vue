<template>
  <div class="h-screen overflow-hidden flex flex-col bg-background">
    <DesktopTitleBar v-if="isDesktop" />
    <div class="flex-1 overflow-auto">
      <slot />
    </div>
    <ToastProvider />
    <ServerStatusButton />
  </div>
</template>

<script setup lang="ts">
import DesktopTitleBar from '@/app/shell/DesktopTitleBar.vue'
import ServerStatusButton from '@/shared/components/ServerStatusButton.vue'
import ToastProvider from '@/shared/components/toast/ToastProvider.vue'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'

const isDesktop = useDesktopBridge().isDesktop()
</script>

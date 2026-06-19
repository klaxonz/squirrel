<template>
  <div class="h-screen overflow-hidden flex flex-col bg-background">
    <DesktopTitleBar v-if="isDesktop" />
    <div class="flex-1 overflow-auto">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import DesktopTitleBar from '@/app/shell/DesktopTitleBar.vue'

const isDesktop = window.desktopApp?.isDesktop === true
</script>

<template>
  <div class="auth-layout">
    <AuthTitleBar v-if="isDesktop" class="auth-layout__chrome" />
    <div class="auth-layout__body">
      <slot />
    </div>
    <ToastProvider />
  </div>
</template>

<script setup lang="ts">
import AuthTitleBar from '@/app/shell/AuthTitleBar.vue'
import ToastProvider from '@/shared/components/toast/ToastProvider.vue'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'

const isDesktop = useDesktopBridge().isDesktop()
</script>

<style scoped>
.auth-layout {
  position: relative;
  display: flex;
  height: 100vh;
  flex-direction: column;
  overflow: hidden;
  background: hsl(var(--background));
}

.auth-layout__chrome {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  z-index: 20;
}

.auth-layout__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}
</style>

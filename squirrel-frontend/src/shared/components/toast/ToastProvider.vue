<template>
  <Teleport to="body">
    <TransitionGroup tag="div" name="app-toast" class="app-toast-stack">
      <ToastContainer v-for="item in toasts" :key="item.id" :toast="item" />
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import ToastContainer from './ToastContainer.vue'
import { toasts } from './useToast'
</script>

<style scoped>
.app-toast-stack {
  position: fixed;
  top: auto;
  left: auto;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: var(--app-toast-z);
  display: flex;
  flex-direction: column;
  gap: var(--app-toast-gap);
  align-items: flex-end;
  pointer-events: none;
}
</style>

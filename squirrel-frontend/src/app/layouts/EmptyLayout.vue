<template>
  <div class="h-screen overflow-hidden flex flex-col bg-background">
    <slot />
    <ServerStatusButton />
  </div>
</template>

<script setup lang="ts">
import ServerStatusButton from '@/shared/components/ServerStatusButton.vue'
</script>

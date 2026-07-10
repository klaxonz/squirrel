<template>
  <!-- AppLayout keeps this full-width rail stationary and moves the workspace
       over it. This wrapper stays chrome-free so Sidebar owns the rail surface. -->
  <Sidebar class="h-full" />
</template>

<script setup lang="ts">
import Sidebar from '@/shared/components/layout/Sidebar.vue'
</script>

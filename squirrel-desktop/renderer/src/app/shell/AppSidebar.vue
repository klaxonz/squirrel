<template>
  <Sidebar class="h-full" :collapsed="collapsed" />
</template>

<script setup lang="ts">
import Sidebar from '@/shared/components/layout/Sidebar.vue'

defineProps<{ collapsed?: boolean }>()
</script>

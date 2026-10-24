<template>
  <Sidebar class="h-full" :collapsed="collapsed" :show-brand="showBrand" />
</template>

<script setup lang="ts">
import Sidebar from '@/shared/components/layout/Sidebar.vue'

withDefaults(defineProps<{
  collapsed?: boolean
  showBrand?: boolean
}>(), {
  showBrand: true,
})
</script>

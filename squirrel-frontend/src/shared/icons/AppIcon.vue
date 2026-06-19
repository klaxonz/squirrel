<template>
  <component :is="iconComponent" :stroke-width="strokeWidth" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { resolveAppIcon, type AppIconName } from '@/shared/icons/app-icons'

const props = withDefaults(defineProps<{
  name: AppIconName
  strokeWidth?: number | string
}>(), {
  strokeWidth: 2,
})

const iconComponent = computed(() => resolveAppIcon(props.name))
</script>

<template>
  <component
    :is="iconComponent"
    :stroke-width="strokeWidth"
    aria-hidden="true"
    focusable="false"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AlertCircle } from 'lucide-vue-next'
import { resolveAppIcon, type AppIconName } from '@/shared/icons/app-icons'

const props = withDefaults(defineProps<{
  name: AppIconName
  strokeWidth?: number | string
}>(), {
  strokeWidth: 2,
})

// Unknown names fall back to AlertCircle at runtime — TS guards at compile time,
// this is for dyncamic resolution paths where a string slipped past the type.
const iconComponent = computed(() => resolveAppIcon(props.name) ?? AlertCircle)
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center overflow-hidden border border-border/40 bg-muted/20 text-muted-foreground/70"
    :class="[sizeClass, roundedClass]"
  >
    <img
      v-if="resolvedIconUrl"
      :src="resolvedIconUrl"
      :alt="String(label || '')"
      class="h-full w-full object-contain"
      loading="lazy"
      @error="loadFailed = true"
    >
    <span v-else class="font-semibold uppercase" :class="textClass">{{ fallbackText }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  iconUrl?: string | null
  label?: string | null
  size?: 'xs' | 'sm' | 'md' | 'lg'
  rounded?: 'sm' | 'md' | 'full'
}>(), {
  iconUrl: null,
  label: '',
  size: 'sm',
  rounded: 'md',
})

const loadFailed = ref(false)

watch(() => props.iconUrl, () => {
  loadFailed.value = false
})

const fallbackText = computed(() => {
  const normalized = String(props.label || '')
    .replace(/[^a-zA-Z0-9]/g, '')
    .toUpperCase()
  return normalized.slice(0, 2) || '?'
})

const resolvedIconUrl = computed(() => {
  if (loadFailed.value || !props.iconUrl) {
    return undefined
  }
  return props.iconUrl
})

const sizeClass = computed(() => {
  if (props.size === 'xs') return 'h-4 w-4'
  if (props.size === 'md') return 'h-8 w-8'
  if (props.size === 'lg') return 'h-10 w-10'
  return 'h-6 w-6'
})

const roundedClass = computed(() => {
  if (props.rounded === 'full') return 'rounded-full'
  if (props.rounded === 'sm') return 'rounded'
  return 'rounded-md'
})

const textClass = computed(() => {
  if (props.size === 'xs') return 'text-[8px]'
  if (props.size === 'md') return 'text-[11px]'
  if (props.size === 'lg') return 'text-xs'
  return 'text-[9px]'
})
</script>

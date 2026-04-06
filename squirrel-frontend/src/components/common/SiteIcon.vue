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
    <Globe v-else aria-hidden="true" :class="iconClass" />
  </span>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Globe } from 'lucide-vue-next'

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

const iconClass = computed(() => {
  if (props.size === 'xs') return 'h-2.5 w-2.5'
  if (props.size === 'md') return 'h-4 w-4'
  if (props.size === 'lg') return 'h-5 w-5'
  return 'h-3.5 w-3.5'
})
</script>

<template>
  <img
    v-if="thumbnailSrc && !showFallback"
    :src="thumbnailSrc"
    :alt="alt"
    loading="lazy"
    decoding="async"
    referrerpolicy="no-referrer"
    class="h-full w-full transition-all duration-300"
    :class="imageClasses"
    @load="handleLoad"
    @error="handleError"
  >

  <div v-else class="absolute inset-0 flex flex-col items-center justify-center bg-muted text-center">
    <span class="flex size-10 items-center justify-center rounded-md border border-border/50 bg-background/55 text-muted-foreground/50 shadow-sm">
      <AppIcon name="imageOff" class="size-5" :stroke-width="1.75" />
    </span>
    <span class="mt-2 max-w-[80%] truncate text-[11px] font-medium text-muted-foreground/60">
      {{ thumbnailSrc ? '封面加载失败' : '暂无封面' }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { useThumbnailRegistry } from './useThumbnailRegistry'

const props = withDefaults(defineProps<{
  src?: string | null
  alt?: string
  fit?: 'contain' | 'cover' | 'responsive'
  interactive?: boolean
  blur?: boolean
}>(), {
  src: '',
  alt: '',
  fit: 'contain',
  interactive: false,
  blur: false,
})

const thumbnailSrc = computed(() => String(props.src || '').trim())
const { imageLoaded, showFallback, handleLoad, handleError } = useThumbnailRegistry(thumbnailSrc)

const fitClass = computed(() => {
  if (props.fit === 'cover') return 'object-cover'
  if (props.fit === 'responsive') return 'object-cover md:object-contain'
  return 'object-contain'
})

const imageClasses = computed(() => [
  fitClass.value,
  props.interactive ? 'group-hover:scale-105 group-hover:brightness-110' : '',
  props.blur ? 'blur-2xl scale-110' : '',
  imageLoaded.value ? 'opacity-100' : 'opacity-0',
])
</script>

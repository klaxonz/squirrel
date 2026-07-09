<template>
  <img
    v-if="thumbnailSrc && !showFallback"
    :src="thumbnailSrc"
    :alt="alt"
    loading="lazy"
    decoding="async"
    referrerpolicy="no-referrer"
    class="video-thumbnail__img h-full w-full transition-opacity duration-200"
    :class="imageClasses"
    @load="handleLoad"
    @error="handleError"
  >

  <div v-else class="video-thumbnail__fallback absolute inset-0 flex flex-col items-center justify-center text-center">
    <span class="flex size-10 items-center justify-center rounded-md border border-white/10 bg-black/35 text-white/55">
      <AppIcon name="imageOff" class="size-5" :stroke-width="1.75" />
    </span>
    <span class="mt-2 max-w-[80%] truncate text-xs font-medium text-white/50">
      {{ thumbnailSrc ? '封面加载失败' : '暂无封面' }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { useThumbnailRegistry } from './useThumbnailRegistry'

const props = withDefaults(defineProps<{
  src?: string | null
  alt?: string
  /** cover fills the frame (default, media cards). contain keeps full image. responsive is an alias of cover. */
  fit?: 'contain' | 'cover' | 'responsive'
  position?: string
  interactive?: boolean
  blur?: boolean
  noFade?: boolean
  imgClass?: string
}>(), {
  src: '',
  alt: '',
  fit: 'cover',
  position: 'center',
  interactive: false,
  blur: false,
  noFade: false,
  imgClass: '',
})

const thumbnailSrc = computed(() => String(props.src || '').trim())
const { imageLoaded, showFallback, handleLoad, handleError } = useThumbnailRegistry(thumbnailSrc)

const fitClass = computed(() => {
  // responsive used to letterbox on desktop (contain), which left light
  // gutters + a white fringe at rounded corners. Media cards always cover.
  if (props.fit === 'contain') return 'object-contain'
  return 'object-cover'
})

const positionClass = computed(() => props.position ? `object-${props.position}` : '')

const imageClasses = computed(() => [
  fitClass.value,
  positionClass.value,
  props.interactive ? 'group-hover:brightness-110' : '',
  props.blur ? 'blur-2xl scale-110' : '',
  props.imgClass,
  props.noFade ? '' : (imageLoaded.value ? 'opacity-100' : 'opacity-0'),
])
</script>

<style scoped>
/* Block-level image avoids the 1px inline baseline gap that reads as a
   hairline under the frame. Do not force absolute fill here — some parents
   (playlist mosaics, non-relative cells) size from the image itself. */
.video-thumbnail__img {
  display: block;
  width: 100%;
  height: 100%;
  /* No transform here — blur mode uses scale utilities on the same element. */
  backface-visibility: hidden;
}

.video-thumbnail__fallback {
  background: hsl(0 0% 0% / 0.55);
}
</style>

<template>
  <img
    v-if="displaySrc && !showFallback && !placeholderImage"
    :src="displaySrc"
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
    <span class="video-thumbnail__fallback-icon size-10 rounded-md">
      <AppIcon name="imageOff" class="size-5" :stroke-width="1.75" />
    </span>
    <span class="video-thumbnail__fallback-label mt-2 max-w-[80%] truncate text-xs font-medium">
      {{ placeholderImage || !thumbnailSrc ? '暂无封面' : '封面加载失败' }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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

const emit = defineEmits<{
  error: []
}>()

const thumbnailSrc = computed(() => String(props.src || '').trim())
const displaySrc = ref(thumbnailSrc.value)
const placeholderImage = ref(false)
watch(thumbnailSrc, (src) => {
  displaySrc.value = src
  placeholderImage.value = false
}, { immediate: true })

const {
  imageLoaded,
  showFallback,
  handleLoad: markLoaded,
  handleError: markImageFailed,
} = useThumbnailRegistry(displaySrc)

const handleLoad = (event: Event) => {
  const img = event.currentTarget as HTMLImageElement
  // YouTube returns a 120x90 grey default for videos with no real cover.
  if (img.naturalWidth > 0 && img.naturalWidth <= 160 && img.naturalHeight <= 120) {
    placeholderImage.value = true
    emit('error')
    return
  }
  markLoaded()
}

const handleError = () => {
  markImageFailed()
  emit('error')
}

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
  background: var(--app-media-thumb-placeholder);
  color: var(--app-media-placeholder-fg);
}

.video-thumbnail__fallback-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--card));
  color: var(--app-media-placeholder-fg);
}

.video-thumbnail__fallback-label {
  color: var(--app-media-placeholder-fg);
}
</style>

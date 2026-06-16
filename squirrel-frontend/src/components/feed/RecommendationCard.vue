<template>
  <article
    class="group w-[18rem] shrink-0 cursor-pointer snap-start"
    @click="$emit('openModal', video)"
  >
    <div
      class="relative aspect-video overflow-hidden bg-muted transition-all duration-300 group-hover:brightness-110 group-hover:shadow-lg"
      :style="{ borderRadius: 'var(--app-card-radius)' }"
    >
      <VideoThumbnail
        :src="video.thumbnail"
        :alt="video.title"
        fit="cover"
        interactive
      />

      <!-- Bottom gradient for overlay readability -->
      <div class="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />

      <!-- Optional duration badge -->
      <div
        v-if="video.duration && showDuration"
        class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm"
      >
        {{ formatDuration(video.duration) }}
      </div>

      <!-- Optional play overlay -->
      <div
        v-if="showPlayOverlay"
        class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100"
      >
        <div class="flex size-10 scale-75 items-center justify-center rounded-full bg-primary/90 text-primary-foreground shadow-lg backdrop-blur-sm transition-transform group-hover:scale-100">
          <AppIcon name="play" class="size-5" />
        </div>
      </div>

      <!-- Optional progress bar (continue watching) -->
      <div
        v-if="showProgress && progress > 0"
        class="absolute inset-x-0 bottom-0 h-1 group-hover:h-1.5 transition-all duration-300 bg-white/30"
      >
        <div class="h-full bg-white transition-all duration-500 ease-out" :style="{ width: `${progress * 100}%` }" />
      </div>
    </div>

    <h3 class="mt-2 line-clamp-2 text-sm font-medium text-foreground/80 transition-colors group-hover:text-primary">
      {{ video.title }}
    </h3>

    <!-- Optional subscription row -->
    <button
      v-if="primarySubscription(video)"
      class="mt-1 flex max-w-full items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      type="button"
      @click.stop="$emit('goToSubscription', primarySubscription(video)?.id)"
    >
      <SubscriptionAvatar
        :src="primarySubscription(video)?.avatar"
        :name="primarySubscription(video)?.name"
        size="sm"
        class="size-4"
      />
      <span class="truncate">{{ primarySubscription(video)?.name }}</span>
    </button>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoThumbnail from '@/components/feed/VideoThumbnail.vue'
import { formatDuration } from '@/utils/dateFormat'

const props = withDefaults(defineProps<{
  video: any
  showDuration?: boolean
  showPlayOverlay?: boolean
  showProgress?: boolean
  showSubscription?: boolean
}>(), {
  showDuration: false,
  showPlayOverlay: false,
  showProgress: false,
  showSubscription: true,
})

defineEmits<{ openModal: [video: any], goToSubscription: [id: any] }>()

const primarySubscription = (video: any) => {
  if (!props.showSubscription) return null
  return Array.isArray(video?.subscriptions) ? video.subscriptions[0] : null
}

const progress = computed(() => {
  const d = Number(props.video?.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video?.last_position || 0) / d) : 0
})
</script>

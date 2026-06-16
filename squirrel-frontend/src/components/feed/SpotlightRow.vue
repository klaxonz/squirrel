<template>
  <section v-if="items.length > 0" class="group/container mb-8 px-6 pt-8">
    <div class="mb-5 flex items-center justify-between">
      <h2 class="flex items-center gap-2 text-lg font-bold tracking-tight text-foreground/90">
        <AppIcon name="star" class="size-5 fill-primary text-primary" />
        精选推荐
      </h2>
      <div class="flex gap-1 opacity-0 transition-opacity duration-200 group-hover/container:opacity-100" :class="{ 'opacity-100': canScrollLeft || canScrollRight }">
        <button
          class="flex size-8 items-center justify-center rounded-full border border-border bg-background/80 shadow-sm transition-all hover:bg-muted disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="!canScrollLeft"
          @click="scroll('left')"
        >
          <AppIcon name="chevronLeft" class="size-4 text-foreground/70" />
        </button>
        <button
          class="flex size-8 items-center justify-center rounded-full border border-border bg-background/80 shadow-sm transition-all hover:bg-muted disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="!canScrollRight"
          @click="scroll('right')"
        >
          <AppIcon name="chevronRight" class="size-4 text-foreground/70" />
        </button>
      </div>
    </div>

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x scroll-smooth"
      @scroll="updateScrollState"
    >
      <article
        v-for="video in items"
        :key="video.id"
        class="group w-[18rem] shrink-0 cursor-pointer snap-start"
        @click="$emit('openModal', video)"
      >
        <div class="relative aspect-video overflow-hidden bg-muted transition-all duration-300 group-hover:brightness-110 group-hover:shadow-lg"
             :style="{ borderRadius: 'var(--app-card-radius)' }">
          <VideoThumbnail
            :src="video.thumbnail"
            :alt="video.title"
            fit="cover"
            interactive
          />
          <!-- Bottom gradient for overlay readability -->
          <div class="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />
          <!-- Spotlight badge -->
          <span class="absolute top-2 left-2 inline-flex items-center gap-1 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary backdrop-blur-sm">
            <AppIcon name="star" class="size-3 fill-primary" />
            推荐
          </span>
        </div>
        <h3 class="mt-2 line-clamp-2 text-sm font-medium text-foreground/80 transition-colors group-hover:text-primary">
          {{ video.title }}
        </h3>
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
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { getVideoList } from '@/api'
import { Logger } from '@/utils/logger'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoThumbnail from '@/components/feed/VideoThumbnail.vue'

defineEmits(['openModal', 'goToSubscription'])

const items = ref<any[]>([])
const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollState = () => {
  if (!scrollContainer.value) return
  const { scrollLeft, scrollWidth, clientWidth } = scrollContainer.value
  canScrollLeft.value = scrollLeft > 0
  canScrollRight.value = scrollLeft < scrollWidth - clientWidth - 2
}

const scroll = (direction: 'left' | 'right') => {
  if (!scrollContainer.value) return
  // 288px card + 16px gap = 304px per item, scroll 2 items
  const scrollAmount = 304 * 2
  scrollContainer.value.scrollTo({
    left: scrollContainer.value.scrollLeft + (direction === 'left' ? -scrollAmount : scrollAmount),
    behavior: 'smooth',
  })
}

const primarySubscription = (video: any) => {
  return Array.isArray(video?.subscriptions) ? video.subscriptions[0] : null
}

const load = async () => {
  try {
    const { data, error } = await getVideoList({
      pageSize: 10,
      page_size: 10,
      category: 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
    })
    if (error) return
    items.value = (data?.data || []).slice(0, 10)
    await nextTick()
    updateScrollState()
  } catch (e) {
    Logger.error('Failed to load spotlight videos:', e)
  }
}

// Re-check scroll state whenever videos change (data loads async)
watch(() => scrollContainer.value?.scrollWidth, () => nextTick(updateScrollState))

onMounted(load)

defineExpose({ refresh: load })
</script>

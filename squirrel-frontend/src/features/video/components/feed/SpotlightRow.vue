<template>
  <section v-if="items.length > 0 || loading" class="group/container mb-8 px-6 pt-8">
    <div class="mb-5 flex items-center justify-between">
      <h2 class="flex items-center gap-2 text-lg font-bold tracking-tight text-foreground/90">
        <AppIcon name="star" class="size-5 fill-amber-400 text-amber-400" />
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
      <RecommendationSkeleton v-if="loading && items.length === 0" :count="6" />
      <RecommendationCard
        v-for="video in items"
        :key="video.id"
        :video="video"
        @openModal="$emit('openModal', video)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem } from '@/features/video/types/video'
import { Logger } from '@/shared/lib/logger'
import AppIcon from '@/shared/icons/AppIcon.vue'
import RecommendationCard from '@/features/video/components/feed/RecommendationCard.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'

defineEmits(['openModal', 'goToSubscription'])

const items = ref<VideoListItem[]>([])
const loading = ref(false)
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

const load = async () => {
  loading.value = true
  try {
    const data = await getVideoList({
      pageSize: 10,
      page_size: 10,
      category: 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
    })
    items.value = (data?.data || []).slice(0, 10)
    await nextTick()
    updateScrollState()
  } catch (e) {
    Logger.error('Failed to load spotlight videos:', e)
  } finally {
    loading.value = false
  }
}

// Re-check scroll state whenever videos change (data loads async)
watch(() => scrollContainer.value?.scrollWidth, () => nextTick(updateScrollState))

onMounted(load)

defineExpose({ refresh: load })
</script>

<template>
  <section v-if="items.length > 0 || loading" class="group/container mb-6 px-6 pt-2">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="flex items-center gap-2 text-xl font-bold tracking-tight text-foreground/90">
        <AppIcon name="star" class="size-5 fill-current text-amber-500" />
        特别关注
      </h2>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
          @click="emit('viewMore')"
        >
          查看更多
          <AppIcon name="chevronRight" class="size-3.5" />
        </button>
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
    </div>

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 scroll-smooth snap-x"
      @scroll="updateScrollState"
    >
      <RecommendationSkeleton v-if="loading && items.length === 0" :count="6" />
      <RecommendationCard
        v-for="item in items"
        :key="item.id"
        :video="item"
        show-duration
        show-play-overlay
        @openModal="emit('openModal', item)"
        @goToSubscription="(id) => emit('goToSubscription', id)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem } from '@/features/video/types/video'
import AppIcon from '@/shared/icons/AppIcon.vue'
import RecommendationCard from '@/features/video/components/feed/RecommendationCard.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'

const emit = defineEmits(['openModal', 'goToSubscription', 'viewMore'])

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
      pageSize: 12,
      page_size: 12,
      category: 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
      special: 'yes',
    })

    items.value = (data?.data || []).slice(0, 12)
    await nextTick()
    updateScrollState()
  } catch {
    // silent — row stays empty
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>

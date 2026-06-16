<template>
  <div class="w-full">
    <!-- List/Grid Container -->
    <div v-if="videos.length > 0"
         :class="uiStore.viewMode === 'grid'
           ? 'grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-6 p-6'
           : 'flex flex-col gap-4 p-6 max-w-4xl mx-auto'">
      <VideoItem
        v-for="video in videos"
        :key="video.id"
        :video="video"
        :show-avatar="showAvatar"
        :sort-by="sortBy"
        :layout="uiStore.viewMode"
        @goToSubscription="$emit('goToSubscription', $event)"
        @openModal="$emit('openModal', video)"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading"
         :class="uiStore.viewMode === 'grid'
           ? 'grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-6 p-6'
           : 'flex flex-col gap-4 p-6 max-w-4xl mx-auto'">
      <VideoSkeleton v-for="i in 12" :key="i" :delay="i * 50" :layout="uiStore.viewMode" />
    </div>

    <!-- Empty State -->
    <div v-if="!loading && videos.length === 0" class="flex flex-col items-center justify-center min-h-[60vh] text-center p-10">
      <div class="w-20 h-20 rounded-full bg-secondary flex items-center justify-center mb-6">
        <AppIcon name="inbox" class="w-10 h-10 text-muted-foreground/30" />
      </div>
      <h3 class="text-xl font-bold text-foreground/60">未找到内容</h3>
      <p class="text-muted-foreground mt-2">请调整筛选条件或搜索关键词后再试。</p>
    </div>

    <!-- Infinite Scroll Trigger -->
    <div ref="loadMoreTrigger" class="h-20 w-full" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

const props = defineProps<{
  videos: any[]
  loading: boolean
  allLoaded: boolean
  showAvatar: boolean
  sortBy?: string
  refreshing: boolean
}>()

const emit = defineEmits(['goToSubscription', 'openModal', 'loadMore'])

const loadMoreTrigger = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

onMounted(() => {
  // Use the specific scroll container as root
  const root = document.getElementById('app-main-scroll')

  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !props.loading && !props.allLoaded) {
      emit('loadMore')
    }
  }, {
    root: root,
    rootMargin: '600px'
  })

  if (loadMoreTrigger.value) observer.observe(loadMoreTrigger.value)
})

onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
</style>

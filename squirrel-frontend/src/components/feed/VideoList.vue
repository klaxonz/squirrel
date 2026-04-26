<template>
  <div class="w-full">
    <!-- Top Progress Bar (Fixed relative to content) -->
    <div v-if="refreshing" class="sticky top-0 left-0 right-0 h-0.5 bg-primary/20 z-50 overflow-hidden">
      <div class="h-full bg-primary animate-progress-slide" />
    </div>

    <!-- Grid Container -->
    <div v-if="videos.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-x-5 gap-y-10 p-6">
      <VideoItem
        v-for="video in videos"
        :key="video.id"
        :video="video"
        :show-avatar="showAvatar"
        :sort-by="sortBy"
        @goToSubscription="$emit('goToSubscription', $event)"
        @openModal="$emit('openModal', video)"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-x-5 gap-y-10 p-6">
      <VideoSkeleton v-for="i in 12" :key="i" :delay="i * 50" />
    </div>

    <!-- Empty State -->
    <div v-if="!loading && videos.length === 0" class="flex flex-col items-center justify-center min-h-[60vh] text-center p-10">
      <div class="w-20 h-20 rounded-full bg-secondary flex items-center justify-center mb-6">
        <Inbox class="w-10 h-10 text-muted-foreground/30" />
      </div>
      <h3 class="text-xl font-bold text-foreground/60">No content found</h3>
      <p class="text-muted-foreground mt-2">Try adjusting your filters or search terms.</p>
    </div>

    <!-- Infinite Scroll Trigger -->
    <div ref="loadMoreTrigger" class="h-20 w-full" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { Inbox } from 'lucide-vue-next'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'

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
@keyframes progress-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.animate-progress-slide {
  animation: progress-slide 1.5s infinite linear;
}
</style>

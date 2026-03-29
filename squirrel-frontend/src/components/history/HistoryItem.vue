<template>
  <div
    class="history-item flex items-center gap-4 p-3 hover:bg-accent/50 rounded-lg group transition-all cursor-pointer border border-transparent hover:border-accent/30"
    @click="$emit('open', video)"
  >
    <!-- Thumbnail Section -->
    <div class="thumbnail-container relative w-44 aspect-video flex-shrink-0 bg-secondary/20 rounded-md overflow-hidden shadow-sm">
      <img
        v-if="video.thumbnail && !showDefaultThumbnail"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="w-full h-full object-cover transition-transform group-hover:scale-105"
        :alt="video.title"
        @error="handleThumbnailError"
      />
      
      <!-- Cinematic Fallback (Matches VideoItem) -->
      <div v-else class="video-terminal-fallback">
        <div class="fallback-noise"></div>
        <div class="fallback-content">
          <span class="fallback-status">信号丢失</span>
          <span class="fallback-id">ID: {{ videoCardId }}</span>
        </div>
      </div>
      
      <!-- Duration Badge -->
      <div class="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 bg-black/80 text-[10px] text-white rounded font-mono backdrop-blur-sm z-10">
        {{ formatDuration(video.duration) }}
      </div>
      
      <!-- Progress Bar -->
      <div
        v-if="video.progress > 0"
        class="absolute bottom-0 left-0 w-full h-[2px] bg-black/20 z-10"
      >
        <div
          class="h-full bg-primary shadow-[0_0_8px_hsl(var(--primary))]"
          :style="{ width: `${video.progress * 100}%` }"
        ></div>
      </div>
    </div>
    
    <!-- Info Section -->
    <div class="info-container flex-grow min-w-0 flex flex-col justify-center gap-1">
      <h4 class="text-sm font-semibold line-clamp-2 leading-snug group-hover:text-primary transition-colors">
        {{ video.title }}
      </h4>
      
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <div class="flex items-center gap-1.5">
          <span class="font-mono text-[9px] bg-accent/80 text-accent-foreground px-1.5 py-0.5 rounded border border-accent/50 uppercase tracking-tighter">
            {{ displaySite }}
          </span>
          
          <div v-if="displayAvatars.length" class="flex items-center -space-x-1">
            <img
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="getImageSrc(avatar.avatar, `history-avatar-${video.id}-${index}`)"
              class="w-4 h-4 rounded-full border border-background object-cover bg-muted"
              referrerpolicy="no-referrer"
              :alt="avatar.name"
              @error="(event) => handleImageError(event, `history-avatar-${video.id}-${index}`)"
            >
          </div>
          
          <span v-if="displayChannel" class="font-medium text-foreground/70">{{ displayChannel }}</span>
        </div>
        
        <div class="flex items-center gap-1">
          <span v-if="displayChannel">•</span>
          <span v-if="video.progress > 0" class="text-primary/80 font-medium">已看 {{ (video.progress * 100).toFixed(0) }}%</span>
          <span v-else>未观看</span>
        </div>

        <div class="flex items-center gap-1">
          <span>•</span>
          <span class="opacity-70">{{ formatLastWatchTime(video.updated_at || video.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Actions Section -->
    <div class="actions-container opacity-0 group-hover:opacity-100 transition-opacity flex items-center pr-2">
      <Button
        variant="ghost"
        size="icon"
        class="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full"
        title="从历史记录中移除"
        @click.stop="$emit('delete', video.history_id ?? video.id)"
      >
        <TrashIcon class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { TrashIcon } from '@heroicons/vue/24/outline'
import { Button } from '@/components/ui/button'
import { formatDate, formatDuration } from '@/utils/dateFormat'
import { formatVideoCardId } from '@/utils/videoCard'
import { useImageFallback } from '@/composables/useImageFallback'

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
})

defineEmits(['open', 'delete'])

const { getImageSrc, handleImageError } = useImageFallback()
const showDefaultThumbnail = ref(false)
const videoCardId = computed(() => formatVideoCardId(props.video?.id))

const handleThumbnailError = () => {
  showDefaultThumbnail.value = true
}

const displayAvatars = computed(() => {
  let avatars = props.video.subscriptions?.map((subscription) => ({
    id: subscription.id,
    name: subscription.name,
    avatar: subscription.avatar,
  })) || []

  if (!avatars.length && props.video.actors) {
    avatars = props.video.actors.map((actor) => ({
      id: actor.id,
      name: actor.name,
      avatar: actor.avatar,
    }))
  }

  return avatars.slice(0, 3)
})

const displaySite = computed(() => {
  if (props.video.site_name) return props.video.site_name;
  if (props.video.subscriptions && props.video.subscriptions.length > 0) {
    return props.video.subscriptions[0].site_name || props.video.subscriptions[0].site;
  }
  return '未知站点';
});

const displayChannel = computed(() => {
  if (props.video.subscriptions && props.video.subscriptions.length > 0) {
    return props.video.subscriptions.map(s => s.name).join(' / ');
  }
  return '';
});

const formatLastWatchTime = (timestamp) => {
  if (!timestamp) return ''
  return formatDate(timestamp)
}
</script>

<style scoped>
.history-item {
  position: relative;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Terminal Fallback Style (Synced with VideoItem) */
.video-terminal-fallback {
  position: absolute;
  inset: 0;
  background: #0a0a0a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.fallback-noise {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
  opacity: 0.05;
}

.fallback-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  z-index: 1;
}

.fallback-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: #ff4d00;
  letter-spacing: 0.25rem;
  font-weight: 800;
  opacity: 0.6;
}

.fallback-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.45rem;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.1em;
}
</style>

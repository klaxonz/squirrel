<template>
  <div
    class="group flex cursor-pointer gap-3 rounded-lg border border-transparent p-2 transition-colors hover:border-border/50 hover:bg-accent/40"
    @click="$emit('open', video)"
  >
    <div class="relative aspect-video w-40 flex-shrink-0 overflow-hidden rounded-md bg-muted md:w-48">
      <img
        v-if="video.thumbnail"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="h-full w-full object-contain"
        :alt="video.title"
      />
      <div v-else class="flex h-full w-full items-center justify-center">
        <AppIcon name="film" class="h-7 w-7 text-muted-foreground/30" />
      </div>

      <!-- Bottom Shadow/Gradient for Overlay Visibility -->
      <div class="absolute bottom-0 inset-x-0 h-10 bg-gradient-to-t from-black/60 to-transparent pointer-events-none z-10" />

      <!-- Progress Bar -->
      <div v-if="video.progress > 0" class="absolute bottom-0 inset-x-0 h-1 group-hover:h-1.5 transition-all duration-300 z-20 bg-white/30">
        <div class="h-full bg-white transition-all duration-500 ease-out" :style="{ width: `${video.progress * 100}%` }" />
      </div>

      <div v-if="video.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium text-white tabular-nums backdrop-blur-sm z-20">
        {{ formatDuration(video.duration) }}
      </div>

      <button
        class="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-md bg-background/90 text-muted-foreground opacity-0 shadow-sm transition-colors group-hover:opacity-100 hover:bg-destructive hover:text-white"
        @click.stop="handleDelete"
      >
        <AppIcon name="trash" class="h-4 w-4" />
      </button>
    </div>

    <div class="flex min-w-0 flex-1 flex-col py-0.5">
      <h3 class="line-clamp-2 text-sm font-semibold leading-snug text-foreground">
        {{ video.title }}
      </h3>

      <div class="mt-auto space-y-1.5">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <div v-if="displayAvatars.length" class="flex -space-x-1.5">
            <img
              v-for="(avatar, i) in displayAvatars"
              :key="i"
              :src="avatar.avatar"
              class="h-5 w-5 rounded-full object-cover ring-2 ring-background"
              :title="avatar.name"
            />
          </div>
          <span class="truncate">{{ displayChannel || '未知作者' }}</span>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span v-if="video.site" class="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            {{ video.site }}
          </span>
          <span class="h-1 w-1 rounded-full bg-border" />
          <span>{{ formatDate(video.played_at) }}</span>
          <template v-if="video.progress > 0">
            <span class="h-1 w-1 rounded-full bg-border" />
            <span>已观看 {{ (video.progress * 100).toFixed(0) }}%</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { formatDate, formatDuration } from '@/utils/dateFormat'

const props = defineProps<{
  video: any
}>()

const emit = defineEmits(['open', 'delete'])

const handleDelete = () => {
  emit('delete', props.video.history_id || props.video.id)
}

const displayAvatars = computed(() => {
  const sources = props.video.subscriptions || props.video.actors || []
  return sources.slice(0, 3).map((s: any) => ({
    name: s.name,
    avatar: s.avatar
  }))
})

const displayChannel = computed(() => {
  const sources = props.video.subscriptions || props.video.actors || []
  return sources.map((s: any) => s.name).join(' / ')
})
</script>

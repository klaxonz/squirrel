<template>
  <div
    class="group relative flex flex-row gap-4 p-3 rounded-2xl transition-all duration-300 hover:bg-accent/50 cursor-pointer"
    @click="$emit('open', video)"
  >
    <!-- 缩略图区域 -->
    <div class="relative flex-shrink-0 w-48 md:w-56 aspect-video rounded-xl overflow-hidden shadow-sm ring-1 ring-border/5">
      <img
        v-if="video.thumbnail"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        :alt="video.title"
      />
      <div v-else class="w-full h-full bg-muted flex items-center justify-center">
        <Film class="w-8 h-8 text-muted-foreground/20" />
      </div>

      <!-- 播放进度 -->
      <div v-if="video.progress > 0" class="absolute bottom-0 left-0 right-0 h-1 bg-black/20 overflow-hidden">
        <div
          class="h-full bg-primary transition-all duration-500 shadow-[0_0_8px_rgba(var(--primary),0.6)]"
          :style="{ width: `${video.progress * 100}%` }"
        />
      </div>

      <!-- 时长 -->
      <div v-if="video.duration" class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded-md bg-black/70 backdrop-blur-md text-[10px] font-bold text-white tabular-nums ring-1 ring-white/10">
        {{ formatDuration(video.duration) }}
      </div>

      <!-- 快捷删除 -->
      <button
        class="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/60 backdrop-blur-md text-white opacity-0 group-hover:opacity-100 transition-all hover:bg-destructive flex items-center justify-center shadow-lg"
        @click.stop="handleDelete"
      >
        <Trash2 class="w-4 h-4" />
      </button>
    </div>

    <!-- 信息区域 -->
    <div class="flex flex-col flex-1 min-w-0 py-1">
      <h3 class="text-base font-bold leading-snug line-clamp-2 group-hover:text-primary transition-colors tracking-tight">
        {{ video.title }}
      </h3>

      <div class="mt-auto flex flex-col gap-1.5">
        <!-- 频道/作者 -->
        <div class="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <div v-if="displayAvatars.length" class="flex -space-x-1.5">
            <img
              v-for="(avatar, i) in displayAvatars"
              :key="i"
              :src="avatar.avatar"
              class="w-5 h-5 rounded-full ring-2 ring-background object-cover"
              :title="avatar.name"
            />
          </div>
          <span class="truncate hover:text-foreground transition-colors">{{ displayChannel || '未知作者' }}</span>
        </div>

        <!-- 元数据 -->
        <div class="flex items-center gap-2 text-[12px] text-muted-foreground/60 font-medium">
          <span v-if="video.site" class="px-1.5 py-0.5 rounded bg-secondary text-[10px] font-black uppercase tracking-wider text-muted-foreground/80">
            {{ video.site }}
          </span>
          <span class="w-1 h-1 rounded-full bg-border" />
          <span>{{ formatDate(video.played_at) }}</span>
          <template v-if="video.progress > 0">
            <span class="w-1 h-1 rounded-full bg-border" />
            <span class="text-primary/70 font-bold">已观看 {{ (video.progress * 100).toFixed(0) }}%</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Film, Trash2 } from 'lucide-vue-next'
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

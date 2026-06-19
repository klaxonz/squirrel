<template>
  <AppPageShell variant="compact">
    <header class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4 lg:px-6">
      <div class="min-w-0">
        <h1 class="truncate text-base font-semibold">{{ pageTitle }}</h1>
        <p class="mt-0.5 text-xs text-muted-foreground">{{ displayVideos.length }} 条记录</p>
      </div>

      <div class="flex items-center gap-2">
        <div v-if="loading" class="hidden gap-1 sm:flex">
          <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
          <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
          <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
        </div>
        <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" @click="loadData">
          <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        </Button>
        <Button v-if="isContinueMode" variant="ghost" class="h-9 rounded-md px-3 text-sm" @click="router.push({ name: 'History' })">
          全部历史
        </Button>
        <button 
          v-if="videos.length && !isContinueMode"
          class="flex h-9 items-center gap-2 rounded-md border border-destructive/20 bg-destructive/10 px-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/15"
          @click="showClearConfirm = true"
        >
          <AppIcon name="trash" class="h-4 w-4" />
          清空
        </button>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto custom-scrollbar">
      <main class="mx-auto w-full max-w-[1200px] p-4 lg:p-6">
        <div v-if="loading && videos.length === 0" class="space-y-8">
          <div v-for="i in 2" :key="i" class="space-y-3">
            <div class="h-7 w-20 animate-pulse rounded-md bg-accent/40" />
            <div class="space-y-2">
              <div v-for="j in 3" :key="j" class="h-28 animate-pulse rounded-lg bg-accent/30" />
            </div>
          </div>
        </div>

        <div v-else-if="groupedVideos.length === 0" class="flex min-h-[24rem] flex-col items-center justify-center text-center">
          <AppIcon name="time" class="h-9 w-9 text-muted-foreground/30" />
          <h2 class="mt-4 text-sm font-semibold">{{ emptyTitle }}</h2>
          <p class="mt-1 text-sm text-muted-foreground">{{ emptyDescription }}</p>
        </div>

        <div v-else class="space-y-10">
          <section v-for="group in groupedVideos" :key="group.date" class="space-y-3">
            <div class="sticky top-0 z-10 flex h-9 items-center justify-between bg-background">
              <h3 class="text-xs font-semibold text-muted-foreground">{{ group.date }}</h3>
              <span class="text-xs text-muted-foreground">{{ group.items.length }} 条</span>
            </div>

            <div class="space-y-2">
              <HistoryItem 
                v-for="video in group.items" 
                :key="video.history_id || video.id"
                :video="video"
                @open="handleOpenVideo"
                @delete="handleDeleteItem"
              />
            </div>
          </section>
        </div>

        <div v-if="loading && videos.length > 0" class="flex justify-center py-10">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
        </div>
      </main>
    </div>

    <Dialog :open="showClearConfirm" @update:open="showClearConfirm = $event">
      <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
        <DialogHeader class="border-b border-border/50 p-5 text-left">
          <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-destructive/10 text-destructive">
            <AppIcon name="trash" class="h-5 w-5" />
          </div>
          <DialogTitle class="text-base font-semibold">清空所有历史记录？</DialogTitle>
          <DialogDescription class="text-sm leading-relaxed text-muted-foreground">
            此操作将永久移除你账户下的所有观看记录，包括各端同步的进度信息。该操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2 bg-muted/30 p-4">
          <Button variant="outline" class="h-9 rounded-md" @click="showClearConfirm = false">取消</Button>
          <Button class="h-9 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90" @click="handleClearHistory">确认清空</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import HistoryItem from '@/components/history/HistoryItem.vue'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useVideoHistory } from '../composables/useVideoHistory'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { formatDate } from '../utils/dateFormat'
import type { VideoHistoryEntry } from '@/types/video'

const router = useRouter()
const route = useRoute()
const { getWatchHistory, clearHistory, deleteHistoryEntry } = useVideoHistory()

const videos = ref<VideoHistoryEntry[]>([])
const loading = ref(false)
const showClearConfirm = ref(false)
const isContinueMode = computed(() => route.query.mode === 'continue')
const pageTitle = computed(() => isContinueMode.value ? '继续观看' : '播放历史')
const emptyTitle = computed(() => isContinueMode.value ? '暂无继续观看' : '暂无历史记录')
const emptyDescription = computed(() => isContinueMode.value ? '未看完的视频会显示在这里。' : '观看过的视频会显示在这里。')

const getProgress = (video: VideoHistoryEntry) => {
  const duration = Number(video.duration || 0)
  return duration > 0 ? Math.min(1, Number(video.last_position || 0) / duration) : 0
}

const displayVideos = computed(() => {
  if (!isContinueMode.value) return videos.value
  return videos.value.filter((video) => {
    const progress = getProgress(video)
    return progress > 0.01 && progress < 0.95
  })
})

const loadData = async () => {
  loading.value = true
  try {
    const data = await getWatchHistory(1, { pageSize: 100 })
    videos.value = data.items || []
  } finally {
    loading.value = false
  }
}

const handleClearHistory = async () => {
  await clearHistory()
  videos.value = []
  showClearConfirm.value = false
}

const handleDeleteItem = async (id: number | string) => {
  await deleteHistoryEntry(id)
  videos.value = videos.value.filter(v => (v.history_id || v.id) !== id)
}

const handleOpenVideo = (video: VideoHistoryEntry) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const groupedVideos = computed(() => {
  const groups: Record<string, VideoHistoryEntry[]> = {}
  displayVideos.value.forEach(v => {
    const date = v.played_at ? formatDate(v.played_at) : '未知时间'
    if (!groups[date]) groups[date] = []
    groups[date].push(v)
  })
  return Object.entries(groups).map(([date, items]) => ({ date, items }))
})

onMounted(() => loadData())
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }
</style>

<template>
  <AppPageShell class="history-page" variant="compact" scrollable>
    <AppToolbarFrame bordered>
      <PageHeader title="播放历史" description="回顾最近观看的内容，同步所有设备进度。">
        <template #actions>
          <button 
            class="flex items-center gap-2 px-4 py-2 rounded-md font-semibold text-[13px] text-destructive bg-destructive/5 hover:bg-destructive/10 transition-colors"
            @click="showClearConfirm = true"
          >
            <AppIcon name="trash" class="w-3.5 h-3.5" />
            清空历史
          </button>
        </template>
      </PageHeader>
    </AppToolbarFrame>

    <div class="app-page-content history-page__content">
      <main class="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-10">
        <!-- 列表区域 -->
        <div class="flex flex-col gap-12">
          <div v-if="loading && videos.length === 0" class="flex flex-col gap-10">
            <div v-for="i in 2" :key="i" class="flex flex-col gap-6">
              <div class="h-8 bg-muted w-32 rounded-xl animate-pulse" />
              <div class="flex flex-col gap-4">
                <div v-for="j in 3" :key="j" class="h-32 bg-muted rounded-lg animate-pulse" />
              </div>
            </div>
          </div>

          <div v-else-if="groupedVideos.length === 0" class="flex flex-col items-center justify-center py-32 text-center">
            <div class="size-20 rounded-lg bg-secondary flex items-center justify-center mb-6">
              <AppIcon name="time" class="w-9 h-9 text-muted-foreground/30" />
            </div>
            <h2 class="text-xl font-semibold mb-3">空空如也</h2>
            <p class="text-muted-foreground max-w-xs font-medium leading-relaxed">
              你还没有任何播放记录。开始探索你感兴趣的内容吧。
            </p>
          </div>

          <div v-else class="flex flex-col gap-16">
            <section v-for="group in groupedVideos" :key="group.date" class="flex flex-col gap-6">
              <div class="sticky top-0 z-10 py-4 bg-background/80 backdrop-blur-md flex items-center gap-6">
                <h3 class="text-base font-semibold">{{ group.date }}</h3>
                <div class="h-px bg-border/50 flex-1" />
                <span class="text-[10px] font-semibold bg-secondary px-3 py-1 rounded-full text-muted-foreground">
                  {{ group.items.length }} 条记录
                </span>
              </div>

              <div class="grid gap-2">
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

          <div v-if="loading && videos.length > 0" class="flex justify-center py-12">
            <LoadingIndicator :loading="true" size="md" />
          </div>
        </div>

        <!-- 侧边栏：统计与筛选 (未来扩展) -->
        <aside class="hidden lg:flex flex-col gap-10">
          <div class="app-surface p-6 flex flex-col gap-6">
            <h4 class="text-sm font-semibold uppercase text-muted-foreground">数据概览</h4>
            <div class="flex flex-col gap-4">
              <div class="flex justify-between items-end">
                <span class="text-muted-foreground font-medium">累计观看</span>
                <span class="text-2xl font-black tabular-nums">{{ videos.length }}</span>
              </div>
              <div class="h-1 bg-border rounded-full overflow-hidden">
                <div class="h-full bg-primary w-2/3" />
              </div>
            </div>
            <p class="text-[12px] text-muted-foreground/60 leading-relaxed font-medium">
              系统将保留过去 90 天内的播放记录，以便你随时找回感兴趣的内容。
            </p>
          </div>

          <div class="px-2 flex flex-col gap-4">
            <h4 class="text-sm font-semibold uppercase text-muted-foreground">隐私说明</h4>
            <p class="text-xs text-muted-foreground/50 leading-loose">
              播放记录仅存储在你的私有账户中。你可以随时选择暂停记录或清空所有数据。清空后，所有同步的设备都将立即失效且无法撤销。
            </p>
          </div>
        </aside>
      </main>
    </div>

    <!-- 确认清空弹窗 -->
    <Dialog :open="showClearConfirm" @update:open="showClearConfirm = $event">
      <DialogContent class="max-w-[400px] rounded-lg p-8">
        <div class="size-16 rounded-lg bg-destructive/10 text-destructive flex items-center justify-center mb-6">
          <AppIcon name="trash" class="w-8 h-8" />
        </div>
        <DialogHeader class="text-left flex flex-col gap-3">
          <DialogTitle class="text-xl font-semibold">确认清空所有历史记录？</DialogTitle>
          <DialogDescription class="text-base text-muted-foreground font-medium leading-relaxed">
            此操作将永久移除你账户下的所有观看记录，包括各端同步的进度信息。该操作不可撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="flex flex-col gap-3 mt-10">
          <button 
            class="w-full py-3 rounded-md bg-destructive text-white font-semibold hover:opacity-90 transition-opacity" 
            @click="handleClearHistory"
          >
            确认清空
          </button>
          <button 
            class="w-full py-3 rounded-md bg-secondary font-semibold hover:bg-secondary/80 transition-colors" 
            @click="showClearConfirm = false"
          >
            取消
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import HistoryItem from '@/components/history/HistoryItem.vue'
import LoadingIndicator from '@/components/feed/LoadingIndicator.vue'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import useVideoHistory from '../composables/useVideoHistory'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { formatDate } from '../utils/dateFormat'

const router = useRouter()
const { getWatchHistory, clearHistory, deleteHistoryEntry } = useVideoHistory()

const videos = ref<any[]>([])
const loading = ref(false)
const showClearConfirm = ref(false)
const searchQuery = ref('')

const loadData = async () => {
  loading.value = true
  try {
    const data = await getWatchHistory(1, { query: searchQuery.value, pageSize: 100 })
    videos.value = data.items || []
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  loadData()
}

const handleClearHistory = async () => {
  await clearHistory()
  videos.value = []
  showClearConfirm.value = false
}

const handleDeleteItem = async (id: any) => {
  await deleteHistoryEntry(id)
  videos.value = videos.value.filter(v => (v.history_id || v.id) !== id)
}

const handleOpenVideo = (video: any) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const groupedVideos = computed(() => {
  const groups: Record<string, any[]> = {}
  videos.value.forEach(v => {
    const date = v.played_at ? formatDate(v.played_at) : '未知时间'
    if (!groups[date]) groups[date] = []
    groups[date].push(v)
  })
  return Object.entries(groups).map(([date, items]) => ({ date, items }))
})

onMounted(() => loadData())
</script>

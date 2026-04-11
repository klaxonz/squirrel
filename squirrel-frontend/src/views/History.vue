<template>
  <div class="history-page flex flex-col h-full bg-background">
    <!-- Header/Toolbar -->
    <div class="toolbar-container border-b border-accent/10 bg-background/50 backdrop-blur-md sticky top-0 z-10">
      <div class="toolbar-inner flex flex-col md:flex-row md:items-center justify-between gap-4 max-w-full mx-auto">
        <div class="flex items-center gap-4 flex-grow">
          <!-- Removed "播放历史" header per user request -->
        </div>

        <div class="flex items-center gap-3">
          <!-- Filters (Site, NSFW) -->
          <div class="flex items-center gap-2">
            <SiteFilter v-model="site" class="h-9" />
            <NsfwFilter v-model="nsfw" class="h-9" />
          </div>

          <div class="h-6 w-px bg-accent/20 mx-1"></div>

          <button
            class="action-btn-minimal"
            :disabled="isRefreshing"
            @click="refreshList"
          >
            <ArrowPathIcon class="h-3 w-3 mr-1.5" :class="{ 'animate-spin': isRefreshing }" />
            刷新
          </button>

          <button
            class="action-btn-minimal is-danger"
            @click="showClearConfirm"
          >
            <TrashIcon class="h-3 w-3 mr-1.5" />
            清空历史
          </button>
        </div>
      </div>
    </div>

    <!-- Content Area -->
    <div class="history-content flex-grow overflow-y-auto scrollbar-hide" ref="scrollContainer" @scroll="handleScroll">
      <div class="history-inner max-w-full mx-auto w-full py-4 pb-20">
        <Transition name="fade-list">
          <!-- Loading State -->
          <div v-if="loading && videos.length === 0" key="skeleton" class="space-y-1 mt-8">
            <HistorySkeleton v-for="i in 10" :key="i" :delay="i * 50" />
          </div>

          <!-- Empty State -->
          <div v-else-if="hasLoadedOnce && groupedVideos.length === 0" key="empty" class="flex flex-col items-center justify-center py-20 text-center">
            <div class="w-20 h-20 bg-accent/20 rounded-full flex items-center justify-center mb-4">
              <ClockIcon class="h-10 w-10 text-muted-foreground/40" />
            </div>
            <h3 class="text-lg font-medium">暂无播放历史</h3>
            <p class="text-sm text-muted-foreground mt-1">
              {{ searchQuery ? '未找到符合搜索条件的记录' : '你观看过的视频会出现在这里' }}
            </p>
          </div>

          <!-- History Groups -->
          <div v-else key="list" class="space-y-8">
            <div v-for="group in groupedVideos" :key="group.date" class="history-group">
              <h3 class="text-sm font-bold text-muted-foreground mb-4 sticky top-0 py-2 bg-background/95 backdrop-blur-sm z-[5] flex items-center gap-2">
                <CalendarIcon class="h-4 w-4" />
                {{ group.date }}
                <span class="text-[10px] font-normal opacity-50 ml-1">({{ group.items.length }})</span>
              </h3>
              
              <div class="space-y-1">
                <TransitionGroup name="history-list">
                  <HistoryItem
                    v-for="video in group.items"
                    :key="video.history_id || video.id"
                    :video="video"
                    @open="handleOpenModal"
                    @delete="handleDeleteItem"
                  />
                </TransitionGroup>
              </div>
            </div>

            <!-- Loading More Indicator -->
            <div v-if="loading" class="py-8 flex justify-center">
              <div class="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-widest">
                <ArrowPathIcon class="h-3 w-3 animate-spin" />
                正在加载更多
              </div>
            </div>
            
            <!-- All Loaded -->
            <div v-if="allLoaded && groupedVideos.length > 0" class="py-12 text-center text-[10px] text-muted-foreground/30 uppercase tracking-[0.4em]">
              没有更多历史记录了
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch, inject, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { 
  TrashIcon, 
  ArrowPathIcon, 
  ClockIcon,
  CalendarIcon
} from '@heroicons/vue/24/outline';
import HistoryItem from '@/components/history/HistoryItem.vue';
import HistorySkeleton from '@/components/history/HistorySkeleton.vue';
import SiteFilter from '@/components/feed/SiteFilter.vue';
import NsfwFilter from '@/components/feed/NsfwFilter.vue';
import useVideoHistory from '../composables/useVideoHistory';
import { formatDate } from '@/utils/dateFormat';
import { Logger } from '@/utils/logger';

const router = useRouter();
const emitter = inject('emitter');
const { getWatchHistory, clearHistory, deleteHistoryEntry } = useVideoHistory();

const videos = ref([]);
const currentPage = ref(1);
const loading = ref(true);
const hasLoadedOnce = ref(false);
const allLoaded = ref(false);
const isRefreshing = ref(false);
const scrollContainer = ref(null);

const PAGE_SIZE = 50;

// Filter and Search State
const nsfw = ref('all');
const site = ref(undefined);
const searchQuery = ref('');

const loadMore = async () => {
  if (allLoaded.value || (loading.value && hasLoadedOnce.value)) return;

  loading.value = true;
  try {
    const data = await getWatchHistory(currentPage.value, {
      nsfw: nsfw.value,
      site: site.value,
      pageSize: PAGE_SIZE,
      query: searchQuery.value
    });
    const newItems = data.items || [];
    
    // Process new items
    const processedNewItems = newItems.map(video => ({
      ...video,
      progress: video.duration ? (video.last_position / video.duration) : 0
    }));

    videos.value = [...videos.value, ...processedNewItems];
    currentPage.value++;

    if (newItems.length === 0) {
      allLoaded.value = true;
    } else if (Number.isFinite(data.total) && data.total > 0) {
      allLoaded.value = videos.value.length >= data.total;
    } else {
      allLoaded.value = newItems.length < PAGE_SIZE;
    }
  } catch (err) {
    Logger.error('Failed to load history', err);
  } finally {
    hasLoadedOnce.value = true;
    loading.value = false;
  }
};

const resetHistoryList = () => {
  hasLoadedOnce.value = false;
  loading.value = true;
  videos.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
};

const refreshList = async () => {
  isRefreshing.value = true;
  resetHistoryList();
  try {
    await loadMore();
  } finally {
    isRefreshing.value = false;
  }
};

// Handle Scroll for Infinite Loading
const handleScroll = (e) => {
  const { scrollTop, clientHeight, scrollHeight } = e.target;
  if (scrollHeight - scrollTop - clientHeight < 200) {
    loadMore();
  }
};

// Watchers for filters
watch([nsfw, site], async () => {
  await refreshList();
});

const showClearConfirm = async () => {
  if (confirm('确定要清空所有历史记录吗？此操作不可恢复。')) {
    try {
      await clearHistory();
      videos.value = [];
    } catch (err) {
      Logger.error('Failed to clear history', err);
    }
  }
};

const handleDeleteItem = async (historyId) => {
  try {
    await deleteHistoryEntry(historyId);
    videos.value = videos.value.filter(v => v.history_id !== historyId);
  } catch (err) {
    Logger.error('Failed to delete history item', err);
  }
};

const handleOpenModal = (video) => {
  router.push(`/video/${video.id}`);
};

// Computed property for grouping
const groupedVideos = computed(() => {
  const groups = {};
  videos.value.forEach(video => {
    // Extract only the date part (YYYY-MM-DD) to ensure grouping by day
    const timestamp = video.played_at;
    let dateKey = '未知日期';
    
    if (timestamp) {
      const raw = typeof timestamp === 'string' ? timestamp : String(timestamp);
      const datePart = raw.includes('T') ? raw.split('T')[0] : raw.split(' ')[0];
      dateKey = formatDate(datePart);
    }

    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(video);
  });
  
  // Convert to array and maintain order (assuming videos are already sorted by time)
  return Object.entries(groups).map(([date, items]) => ({
    date,
    items
  }));
});

onMounted(() => {
  loadMore();
  emitter?.on?.('search:history', (query) => {
    searchQuery.value = query || '';
    refreshList();
  });
})

onUnmounted(() => {
  emitter?.off?.('search:history');
})
</script>

<style scoped>
.toolbar-container {
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .toolbar-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container {
    padding: 0 2rem;
  }
}

.toolbar-inner {
  padding: 1rem;
}

@media (min-width: 640px) {
  .toolbar-inner {
    padding: 0;
  }
}

.history-inner {
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .history-inner {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .history-inner {
    padding: 0 2rem;
  }
}

.history-page {
  height: 100%;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.history-group h3 {
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.fade-list-enter-active,
.fade-list-leave-active {
  transition: opacity 0.4s ease;
}

.fade-list-enter-from,
.fade-list-leave-to {
  opacity: 0;
}

.history-list-enter-active {
  transition: all 0.3s ease;
}

.history-list-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

/* Minimal Terminal Buttons */
.action-btn-minimal {
  display: flex;
  align-items: center;
  background: transparent;
  border: 1px solid hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground) / 0.4);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.55rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  padding: 0.4rem 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 2px;
}

.action-btn-minimal:hover:not(:disabled) {
  border-color: hsl(var(--foreground) / 0.25);
  color: hsl(var(--foreground));
  background: hsl(var(--foreground) / 0.02);
}

.action-btn-minimal:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn-minimal.is-danger:hover {
  border-color: hsl(var(--primary) / 0.4);
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.05);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

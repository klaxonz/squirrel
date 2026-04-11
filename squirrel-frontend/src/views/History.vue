<template>
  <div class="history-page flex flex-col h-full bg-background">
    <!-- Header/Toolbar -->
    <div class="toolbar-container">
      <FeedToolbar
        class="history-toolbar"
        :show-tabs="false"
        :tabs-with-counts="[]"
        :nsfw="nsfw"
        :site="site"
        :is-refreshing="isRefreshing"
        @update:nsfw="(value) => { nsfw = value }"
        @update:site="(value) => { site = value }"
        @refresh="refreshList"
      >
        <template #actions>
          <div class="toolbar-left">
            <div class="sort-tabs" role="tablist" aria-label="排序方式">
              <button
                v-for="opt in sortOptions"
                :key="opt.value"
                class="sort-tab"
                :class="{ 'is-active': sortBy === opt.value }"
                role="tab"
                :aria-selected="sortBy === opt.value"
                @click="handleSortChange(opt.value)"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div class="toolbar-right">
            <button
              class="action-btn-minimal is-danger"
              @click="showClearConfirm = true"
            >
              <TrashIcon class="h-3 w-3 mr-1.5" />
              清空历史
            </button>
          </div>
        </template>
      </FeedToolbar>
    </div>

    <!-- Clear Confirmation Dialog -->
    <Dialog :open="showClearConfirm" @update:open="showClearConfirm = $event">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>清空播放历史</DialogTitle>
          <DialogDescription>
            确定要清空所有历史记录吗？此操作不可恢复。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button variant="secondary" @click="showClearConfirm = false">取消</Button>
          <Button variant="destructive" @click="handleClearHistory">确认清空</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Content Area -->
    <div class="history-content flex-grow overflow-y-auto scrollbar-hide" ref="scrollContainer" @scroll="handleScroll">
      <div class="history-inner max-w-full mx-auto w-full py-4 pb-20">
        <Transition name="fade-list">
          <!-- Loading State -->
          <div v-if="loading && videos.length === 0" key="skeleton" class="space-y-1 mt-8">
            <HistorySkeleton v-for="i in 10" :key="i" :delay="i * 50" />
          </div>

          <!-- Empty State -->
          <div v-else-if="hasLoadedOnce && groupedVideos.length === 0" key="empty" class="history-empty-card">
            <div class="empty-terminal-fallback">
              <div class="fallback-noise"></div>
              <div class="fallback-content">
                <span class="fallback-status">{{ searchQuery ? '未找到匹配' : '暂无记录' }}</span>
                <span class="fallback-id">{{ searchQuery ? '搜索结果为空' : '播放历史为空' }}</span>
              </div>
            </div>
            <p class="empty-hint">{{ searchQuery ? '尝试更换关键词' : '你观看过的视频会出现在这里' }}</p>
          </div>

          <!-- History Groups -->
          <div v-else key="list" class="space-y-8">
            <div v-for="group in groupedVideos" :key="group.date" class="history-group">
              <h3 class="history-date-header">
                <CalendarIcon class="h-4 w-4" />
                <span class="date-label">{{ group.date }}</span>
                <span class="date-count">({{ group.items.length }})</span>
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
            <div v-if="loading" class="history-loading-indicator">
              <span class="loading-dot"></span>
              <span class="loading-text">加载中</span>
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
import { TrashIcon, CalendarIcon } from '@heroicons/vue/24/outline';
import FeedToolbar from '@/components/feed/FeedToolbar.vue';
import HistoryItem from '@/components/history/HistoryItem.vue';
import HistorySkeleton from '@/components/history/HistorySkeleton.vue';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import useVideoHistory from '../composables/useVideoHistory';
import { Logger } from '@/utils/logger';

const router = useRouter();
const emitter = inject('emitter');
const { getWatchHistory, clearHistory, deleteHistoryEntry } = useVideoHistory();

const videos = ref([]);
const currentPage = ref(1);
const loading = ref(false);
const hasLoadedOnce = ref(false);
const allLoaded = ref(false);
const isRefreshing = ref(false);
const scrollContainer = ref(null);
const historyLoadVersion = ref(0);

const PAGE_SIZE = 50;

// Filter and Sort State
const nsfw = ref('all');
const site = ref(undefined);
const searchQuery = ref('');
const sortBy = ref('recent');
const showClearConfirm = ref(false);

const sortOptions = [
  { value: 'recent', label: '最近' },
  { value: 'oldest', label: '最早' },
];

const handleSortChange = (value) => {
  sortBy.value = value;
  sortVideos();
};

const sortVideos = () => {
  const sorted = [...videos.value];
  if (sortBy.value === 'oldest') {
    sorted.sort((a, b) => new Date(a.played_at || 0) - new Date(b.played_at || 0));
  } else {
    sorted.sort((a, b) => new Date(b.played_at || 0) - new Date(a.played_at || 0));
  }
  videos.value = sorted;
};

const loadMore = async () => {
  if (allLoaded.value || loading.value) return;

  const requestedPage = currentPage.value;
  const requestVersion = historyLoadVersion.value;
  loading.value = true;
  try {
    const data = await getWatchHistory(requestedPage, {
      nsfw: nsfw.value,
      site: site.value,
      pageSize: PAGE_SIZE,
      query: searchQuery.value
    });

    if (requestVersion !== historyLoadVersion.value) {
      return;
    }

    const newItems = data.items || [];

    const processedNewItems = newItems.map(video => ({
      ...video,
      progress: video.duration ? (video.last_position / video.duration) : 0
    }));

    if (requestedPage === 1) {
      videos.value = processedNewItems;
    } else {
      const existingIds = new Set(videos.value.map(video => video.history_id || video.id));
      const dedupedNewItems = processedNewItems.filter(video => !existingIds.has(video.history_id || video.id));
      videos.value = [...videos.value, ...dedupedNewItems];
    }
    currentPage.value = requestedPage + 1;

    // Apply sorting
    sortVideos();

    if (newItems.length === 0) {
      allLoaded.value = true;
    } else if (Number.isFinite(data.total) && data.total > 0) {
      allLoaded.value = videos.value.length >= data.total;
    } else {
      allLoaded.value = newItems.length < PAGE_SIZE;
    }
  } catch (err) {
    if (requestVersion !== historyLoadVersion.value) {
      return;
    }
    Logger.error('Failed to load history', err);
  } finally {
    if (requestVersion === historyLoadVersion.value) {
      hasLoadedOnce.value = true;
      loading.value = false;
    }
  }
};

const resetHistoryList = () => {
  historyLoadVersion.value += 1;
  hasLoadedOnce.value = false;
  loading.value = false;
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

const handleClearHistory = async () => {
  try {
    await clearHistory();
    videos.value = [];
    showClearConfirm.value = false;
  } catch (err) {
    Logger.error('Failed to clear history', err);
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
    const timestamp = video.played_at;
    let dateKey = '未知日期';

    if (timestamp) {
      const raw = typeof timestamp === 'string' ? timestamp : String(timestamp);
      const datePart = raw.includes('T') ? raw.split('T')[0] : raw.split(' ')[0];

      const date = new Date(datePart);
      date.setHours(0, 0, 0, 0);

      dateKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }

    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(video);
  });

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
.history-page {
  height: 100%;
}

.toolbar-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
  border-bottom: 1px solid hsl(var(--accent) / 0.1);
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

.history-toolbar {
  padding: 0.75rem 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Sort Tabs */
.sort-tabs {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  background: hsl(var(--secondary) / 0.3);
  border-radius: calc(var(--radius-sm) + 2px);
  padding: 2px;
}

.sort-tab {
  padding: 0.2rem 0.6rem;
  border-radius: calc(var(--radius-sm) - 1px);
  font-size: 0.7rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground) / 0.7);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  letter-spacing: 0.02em;
}

.sort-tab:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--background) / 0.5);
}

.sort-tab.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  box-shadow: 0 1px 3px hsl(var(--border) / 0.4);
}

/* History Inner */
.history-inner {
  width: 100%;
  margin: 0 auto;
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

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

/* Date Group Header */
.history-date-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  margin-bottom: 0;
  background: hsl(var(--background));
  border-radius: 0;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: hsl(var(--muted-foreground));
  position: sticky;
  top: 0;
  z-index: 10;
  transition: all 0.2s ease;
}

.history-date-header::after {
  content: '';
  position: absolute;
  left: -1px;
  right: -1px;
  bottom: -0.5rem;
  height: 0.5rem;
  background: hsl(var(--background));
  pointer-events: none;
}

.date-label {
  font-weight: 700;
}

.date-count {
  font-size: 0.55rem;
  font-weight: 400;
  opacity: 0.5;
  margin-left: 0.25rem;
}

/* Empty State */
.history-empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  gap: 1.5rem;
}

.empty-terminal-fallback {
  position: relative;
  width: 6rem;
  aspect-ratio: 16/9;
  background: hsl(var(--secondary) / 0.5);
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
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
  gap: 0.3rem;
  z-index: 1;
}

.fallback-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  color: hsl(var(--primary));
  letter-spacing: 0.2em;
  font-weight: 800;
  opacity: 0.7;
}

.fallback-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.45rem;
  color: hsl(var(--muted-foreground) / 0.4);
  letter-spacing: 0.08em;
}

.empty-hint {
  font-size: 0.8rem;
  color: hsl(var(--muted-foreground) / 0.6);
}

/* Loading Indicator */
.history-loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem 0;
  color: hsl(var(--muted-foreground) / 0.5);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
}

.loading-dot {
  width: 4px;
  height: 4px;
  background: hsl(var(--primary));
  border-radius: 50%;
  animation: pulse-dot 1s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* Action Buttons */
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

/* Transitions */
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

/* Responsive */
@media (max-width: 640px) {
  .toolbar-left {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }
}
</style>

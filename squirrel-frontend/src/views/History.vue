<template>
  <div class="history-page flex h-full flex-col bg-background text-foreground">
    <!-- Header/Toolbar -->
    <div class="history-toolbar__container">
      <FeedToolbar
        class="history-toolbar"
        :show-tabs="false"
        :tabs="[]"
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
              <Icon icon="lucide:trash-2" />
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
    <div class="history-content scrollbar-hide" ref="scrollContainer" @scroll="handleScroll">
      <div class="history-content__inner">
          <!-- Loading State -->
          <div v-if="loading && videos.length === 0" class="history-state">
            <LoadingIndicator :loading="true" text="正在加载历史记录" />
          </div>

          <!-- Empty State -->
          <div v-else-if="hasLoadedOnce && groupedVideos.length === 0" class="history-empty-card">
            <p class="history-empty-card__eyebrow">历史记录</p>
            <h2 class="history-empty-card__title">{{ searchQuery ? '未找到匹配' : '暂无记录' }}</h2>
            <p class="history-empty-card__copy">{{ searchQuery ? '尝试更换关键词' : '你观看过的视频会出现在这里' }}</p>
          </div>

          <!-- History Groups -->
          <div v-else class="history-groups">
            <div v-for="group in groupedVideos" :key="group.date" class="history-group">
              <h3 class="history-date-header">
                <Icon icon="lucide:calendar" class="history-date-header__icon" />
                <span class="history-date-header__label">{{ group.date }}</span>
                <span class="history-date-header__meta-dot" aria-hidden="true"></span>
                <span class="history-date-header__count">{{ group.items.length }} 条</span>
              </h3>

              <div class="history-group__items">
                <HistoryItem
                  v-for="video in group.items"
                  :key="video.history_id || video.id"
                  :video="video"
                  @open="handleOpenModal"
                  @delete="handleDeleteItem"
                />
              </div>
            </div>

            <!-- Loading More Indicator -->
            <div v-if="loading && videos.length > 0" class="history-loading">
              <LoadingIndicator :loading="true" size="sm" />
            </div>

            <!-- All Loaded -->
            <div v-if="allLoaded && groupedVideos.length > 0" class="history-all-loaded">
              没有更多历史记录了
            </div>
          </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch, inject, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { Icon } from '@iconify/vue';
import FeedToolbar from '@/components/feed/FeedToolbar.vue';
import LoadingIndicator from '@/components/feed/LoadingIndicator.vue';
import HistoryItem from '@/components/history/HistoryItem.vue';
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
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed';
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
  rememberVideoPlaybackSeed(video);
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
  min-height: 100%;
}

.history-toolbar__container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
  border-bottom: 1px solid hsl(var(--accent) / 0.1);
}

@media (min-width: 640px) {
  .history-toolbar__container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .history-toolbar__container {
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

/* Content */
.history-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.history-content__inner {
  width: 100%;
  margin: 0 auto;
  padding: 0.75rem 1rem 1.25rem;
}

@media (min-width: 640px) {
  .history-content__inner {
    padding: 0.75rem 1.5rem 1.25rem;
  }
}

@media (min-width: 1024px) {
  .history-content__inner {
    padding: 0.75rem 2rem 1.25rem;
  }
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

/* States */
.history-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 18rem;
}

.history-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 0;
}

/* Empty Card */
.history-empty-card {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: 1.25rem;
  padding: 2rem;
  border: 1px dashed hsl(var(--border) / 0.6);
  border-radius: var(--radius-lg);
}

.history-empty-card__eyebrow {
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: hsl(var(--primary));
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.history-empty-card__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.history-empty-card__copy {
  margin: 0;
  max-width: 22rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.6;
}

/* Date Group Header */
.history-date-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0;
  margin-bottom: 0;
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
  position: sticky;
  top: 0;
  z-index: 10;
  background: hsl(var(--background));
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

.history-date-header__icon {
  font-size: 0.75rem;
  opacity: 0.6;
}

.history-date-header__label {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.history-date-header__meta-dot {
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 999px;
  background: hsl(var(--border));
}

.history-date-header__count {
  font-weight: 400;
  font-size: 0.6rem;
  opacity: 0.7;
}

/* Groups */
.history-groups {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.history-group__items {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* All Loaded */
.history-all-loaded {
  padding: 3rem 0;
  text-align: center;
  font-size: 0.6rem;
  color: hsl(var(--muted-foreground) / 0.3);
  text-transform: uppercase;
  letter-spacing: 0.4em;
}

/* Action Buttons */
.action-btn-minimal {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.4);
  color: hsl(var(--muted-foreground) / 0.7);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 0.3rem 0.625rem;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: var(--radius-md);
}

.action-btn-minimal:hover:not(:disabled) {
  border-color: hsl(var(--border));
  color: hsl(var(--foreground));
  background: hsl(var(--secondary) / 0.3);
}

.action-btn-minimal.is-danger:hover {
  border-color: hsl(var(--primary) / 0.4);
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.05);
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

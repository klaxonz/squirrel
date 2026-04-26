<template>
  <AppPageShell class="history-page">
    <!-- Header/Toolbar -->
    <AppToolbarFrame class="history-toolbar__container" bordered>
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
            <AppSegmentedControl
              v-model="sortBy"
              class="sort-tabs"
              :options="sortOptions"
              aria-label="排序方式"
              @change="handleSortChange"
            />
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
    </AppToolbarFrame>

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
          <AppEmptyState
            v-else-if="hasLoadedOnce && groupedVideos.length === 0"
            class="history-empty-card"
            eyebrow="历史记录"
            :title="searchQuery ? '未找到匹配' : '暂无记录'"
            :copy="searchQuery ? '尝试更换关键词' : '你观看过的视频会出现在这里'"
          />

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
  </AppPageShell>
</template>

<script setup>
import { onMounted, ref, computed, watch, inject, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { Icon } from '@iconify/vue';
import AppEmptyState from '@/components/layout/AppEmptyState.vue';
import AppPageShell from '@/components/layout/AppPageShell.vue';
import AppSegmentedControl from '@/components/layout/AppSegmentedControl.vue';
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue';
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

<style scoped src="../styles/views/History.css"></style>

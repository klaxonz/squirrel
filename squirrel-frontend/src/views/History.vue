<template>
  <div class="history-page flex flex-col h-full">
    <!-- 顶部操作栏 -->
    <div class="toolbar-container">
      <FeedToolbar
        :show-tabs="false"
        :show-nsfw="true"
        :show-site="true"
        :show-sort="false"
        :show-refresh="true"
        :is-refreshing="isRefreshing"
        :tabs-with-counts="[]"
        :nsfw="nsfw"
        :site="site"
        @update:nsfw="(v) => nsfw = v"
        @update:site="(v) => site = v"
        @refresh="refreshList"
      >
        <button
          @click="showClearConfirm"
          class="ml-2 px-3 py-1.5 min-w-[100px] bg-bg-elevated hover:bg-bg-hover text-text-primary rounded-full flex items-center justify-center transition-colors whitespace-nowrap text-xs font-medium"
        >
          <TrashIcon class="h-4 w-4" />
          <span class="ml-1">清空历史</span>
        </button>
      </FeedToolbar>
    </div>

    <!-- 视频列表容器 -->
    <div class="video-container flex-grow">
      <VideoList
        :videos="processedVideos"
        :loading="loading"
        :allLoaded="allLoaded"
        :showAvatar="true"
        @loadMore="loadMore"
        @openModal="handleOpenModal"
        @goToSubscription="handleGoToSubscription"
      />
    </div>
  </div>
</template>

<script setup>
import {onMounted, ref, computed, watch} from 'vue';
import {useRouter} from 'vue-router';
import { TrashIcon } from '@heroicons/vue/24/outline';
import VideoList from '../components/VideoList.vue';
import FeedToolbar from '../components/feed/FeedToolbar.vue';
import useVideoHistory from '../composables/useVideoHistory';
import { Logger } from '../utils/logger'

const router = useRouter();
const {getWatchHistory, clearHistory} = useVideoHistory();

const videos = ref([]);
const currentPage = ref(1);
const loading = ref(false);
const allLoaded = ref(false);
const isRefreshing = ref(false);

const PAGE_SIZE = 50;


// 筛选状态
const nsfw = ref('all');
const site = ref(undefined);

const loadMore = async () => {
  if (loading.value || allLoaded.value) return;

  loading.value = true;
  let newItems = [];
  try {
    const data = await getWatchHistory(currentPage.value, {
      nsfw: nsfw.value,
      site: site.value,
      pageSize: PAGE_SIZE
    });
    newItems = data.items || [];
    videos.value = [...videos.value, ...newItems];
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
    loading.value = false;
  }

  if (!loading.value && !allLoaded.value && videos.value.length < PAGE_SIZE && newItems.length > 0) {
    await loadMore();
  }
};


const refreshList = async () => {
  isRefreshing.value = true;
  videos.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  try {
    await loadMore();
  } finally {
    isRefreshing.value = false;
  }
};

// 监听筛选变化，重新加载数据
watch([nsfw, site], () => {
  refreshList();
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

const handleOpenModal = (video) => {
  // 从列表页进入时，直接跳转，不传递复杂对象
  router.push(`/video/${video.id}`);
};

const handleGoToSubscription = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`);
};

// 添加计算属性来处理视频进度
const processedVideos = computed(() => {
  return videos.value.map(video => ({
    ...video,
    showProgress: true,
    progress: video.duration ? (video.last_position / video.duration) : 0
  }));
});

onMounted(() => {
  loadMore();
})
</script>

<style scoped>
.history-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.toolbar-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding: 0 1rem;
  width: 100%;
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

.video-container {
  flex: 1;
  overflow: hidden;
}
</style> 

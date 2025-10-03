<template>
  <div class="history-page flex flex-col h-full">
    <!-- 顶部操作栏 -->
    <div class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8">
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
          class="ml-2 px-3 py-1.5 min-w-[100px] bg-white/10 hover:bg-white/15 text-white rounded-full flex items-center justify-center transition-colors whitespace-nowrap text-xs font-medium"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
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
import VideoList from '../components/VideoList.vue';
import FeedToolbar from '../components/feed/FeedToolbar.vue';
import useVideoHistory from '../composables/useVideoHistory';
import useCustomToast from '../composables/useToast';

const router = useRouter();
const {getWatchHistory, clearHistory} = useVideoHistory();
const {displayToast} = useCustomToast();

const videos = ref([]);
const currentPage = ref(1);
const loading = ref(false);
const allLoaded = ref(false);
const isRefreshing = ref(false);

// 筛选状态
const nsfw = ref('all');
const site = ref(undefined);

const loadMore = async () => {
  if (loading.value || allLoaded.value) return;

  loading.value = true;
  try {
    const data = await getWatchHistory(currentPage.value, {
      nsfw: nsfw.value,
      site: site.value,
      pageSize: 20
    });
    videos.value = [...videos.value, ...data.items];
    currentPage.value++;
    allLoaded.value = data.items.length < 20;
  } catch (err) {
    displayToast(err.message, {type: 'error'});
  } finally {
    loading.value = false;
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
  if (confirm('确定要清空所有观看历史吗？此操作不可恢复。')) {
    try {
      await clearHistory();
      videos.value = [];
      displayToast('观看历史已清空');
    } catch (err) {
      displayToast('清空观看历史失败', {type: 'error'});
    }
  }
};

const handleOpenModal = (video) => {
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

.video-container {
  flex: 1;
  overflow: hidden;
}
</style> 
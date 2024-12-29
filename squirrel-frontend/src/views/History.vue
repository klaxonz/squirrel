<template>
  <div class="history-page flex flex-col h-full bg-[#0f0f0f] text-white">
    <div class="flex justify-between items-center px-4 py-4">
      <h1 class="text-xl font-medium">观看历史</h1>
      <button
        @click="showClearConfirm"
        class="flex items-center px-3 py-1.5 text-[#f1f1f1] hover:bg-[#ffffff1a] rounded-full transition-colors text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        清空观看历史
      </button>
    </div>

    <div class="flex-1 overflow-y-auto scrollbar-hide">
      <div class="max-w-[1800px] mx-auto px-4">
        <VideoList
          :videos="processedVideos"
          :loading="loading"
          :allLoaded="allLoaded"
          :showAvatar="true"
          @loadMore="loadMore"
          @openModal="handleOpenModal"
          @goToChannel="handleGoToChannel"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import {inject, onMounted, ref, computed} from 'vue';
import {useRouter} from 'vue-router';
import VideoList from '../components/VideoList.vue';
import {useVideoHistory} from '../composables/useVideoHistory';
import useCustomToast from '../composables/useToast';

const router = useRouter();
const emitter = inject('emitter');
const {getWatchHistory, clearHistory} = useVideoHistory();
const {displayToast} = useCustomToast();

const videos = ref([]);
const currentPage = ref(1);
const loading = ref(false);
const allLoaded = ref(false);

const loadMore = async () => {
  if (loading.value || allLoaded.value) return;

  loading.value = true;
  try {
    const data = await getWatchHistory(currentPage.value);
    videos.value = [...videos.value, ...data.items];
    currentPage.value++;
    allLoaded.value = data.items.length < 20;
  } catch (err) {
    displayToast(err.message, {type: 'error'});
  } finally {
    loading.value = false;
  }
};

const showClearConfirm = async () => {
  if (confirm('确定要清空所有观看历史吗？此操作不可恢复。')) {
    try {
      await clearHistory();
      videos.value = [];
      displayToast('历史记录已清空');
    } catch (err) {
      displayToast('清空历史记录失败', {type: 'error'});
    }
  }
};

const handleOpenModal = (video) => {
  emitter.emit('openVideoModal', {video});
};

const handleGoToChannel = (channelId) => {
  router.push(`/channel/${channelId}/all`);
};

// 添加计算属性来处理视频进度
const processedVideos = computed(() => {
  return videos.value.map(video => ({
    ...video,
    showProgress: true,
    progress: video.last_position / video.total_duration
  }));
});

onMounted(() => {
  loadMore();
})
</script>

<style scoped>
.history-page {
  height: 100vh;
}

.scrollbar-hide {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.scrollbar-hide::-webkit-scrollbar {
  display: none; /* Chrome, Safari and Opera */
  width: 0;
  height: 0;
}
</style> 
<template>
  <div class="history-page bg-[#0f0f0f] min-h-screen text-white">
    <div class="max-w-7xl mx-auto px-4 py-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">观看历史</h1>
        <button
            @click="showClearConfirm"
            class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
        >
          清空历史记录
        </button>
      </div>

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
<template>
  <div class="latest-videos flex flex-col h-full mx-4">
    <SearchBar class="pt-4" @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div class="video-container pt-1 flex-grow">
      <router-view 
        v-slot="{ Component }" 
      >
        <component
          :is="Component"
          :active-tab="activeTab"
          :search-query="searchQuery"
          :selected-channel-id="channelId"
          @update-counts="updateCounts"
          @openModal="openVideoModal"
          @goToChannel="goToChannelDetail"
        />
      </router-view>
    </div>

    <VideoModal
      :isOpen="isModalOpen"
      :video="selectedVideo"
      :playlist="currentPlaylist"
      @close="closeVideoModal"
      @videoPlay="onVideoPlay"
      @videoPause="onVideoPause"
      @videoEnded="onVideoEnded"
      @changeVideo="handleChangeVideo"
    />
  </div>

  <div v-if="error" class="text-center py-4 text-red-500">
    {{ error }}
  </div>

  <Teleport to="body">
    <div v-if="showToast" class="toast-message">
      {{ toastMessage }}
    </div>
  </Teleport>
</template>

<script setup>
import {onMounted, onUnmounted, inject, ref, watch, computed} from 'vue';
import {useRoute, useRouter} from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import useVideoOperations from '../composables/useVideoOperations';
import useToast from '../composables/useToast';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import VideoModal from '../components/VideoModal.vue';

const router = useRouter();
const emitter = inject('emitter');

const {
  videoContainer,
  videos,
  error,
  loadMore,
} = useLatestVideos();

const { toastMessage, showToast, displayToast } = useToast();

const {
  playVideo,
  changeVideo,
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
} = useVideoOperations(videos);

const activeTab = ref('all');
const route = useRoute();

// 使用 computed 获取路由参数，这样可以响应式地获取参数变化
const channelId = computed(() => route.params.id);

const isModalOpen = ref(false);
const selectedVideo = ref(null);
const currentPlaylist = ref([]);
const tabsWithCounts = ref([
  {
    value: 'all',
    count: 0,
    label: '全部'
  },
  {
    value: 'unread',
    count: 0,
    label: '未读'
  },
  {
    value: 'read',
    count: 0,
    label: '已读'
  }
]);

const searchQuery = ref('');

const updateCounts = (counts) => {
  tabsWithCounts.value = counts;
};

const handleSearch = (keyword) => {
  console.log('Search query changed:', keyword)
  searchQuery.value = keyword;
};

const openVideoModal = async (video, videos, startTime = 0) => {
  emitter.emit('closeMiniPlayer');
  video.currentTime = startTime;
  selectedVideo.value = video;
  currentPlaylist.value = videos;
  isModalOpen.value = true;
  await playVideo(video)
};

const closeVideoModal = () => {
  isModalOpen.value = false;
  selectedVideo.value = null;
};

onMounted(() => {
  console.log('onMounted', channelId.value);
  emitter.on('openVideoModal', handleOpenVideoModal);
});

onUnmounted(() => {
  if (videoContainer.value) {
    videoContainer.value.style.overscrollBehavior = 'auto';
  }

  window.onpopstate = null;
  emitter.off('openVideoModal', handleOpenVideoModal);
});

const goToChannelDetail = (newChannelId) => {
  console.log('goToChannelDetail', newChannelId);
  router.replace(`/channel/${newChannelId}/all`);
};

const handleChangeVideo = async (newVideo) => {
  try {
    const updatedVideo = await changeVideo(newVideo);
    if (updatedVideo) {
      selectedVideo.value = updatedVideo;
    }
  } catch (err) {
    console.error('切换视频失败:', err);
    displayToast('切换视频失败');
  }
};

const handleOpenVideoModal = (data) => {
  if (data.video) {
    openVideoModal(data.video, data.currentTime);
  }
};

watch(() => activeTab.value, (newVal) => {
  router.push(`/videos/${newVal}`);
});

</script>

<style src="./LatestVideos.css" scoped></style>

<style scoped>
.latest-videos {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.video-container {
  flex: 1;
  overflow: hidden;
}
</style>

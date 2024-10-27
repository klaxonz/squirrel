<template>
  <div class="latest-videos flex flex-col h-full">
    <SearchBar class="pt-4" @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div class="video-container pt-1 flex-grow">
      <VideoList
        :videos="filteredVideos[activeTab]"
        :loading="loading"
        :allLoaded="allLoaded"
        :showAvatar="true"
        :setVideoRef="setVideoRef"
        :is-channel-page="false"
        :active-tab="activeTab"
        @loadMore="loadMore"
        @play="playVideo"
        @videoPlay="onVideoPlay"
        @videoPause="onVideoPause"
        @videoEnded="onVideoEnded"
        @toggleOptions="toggleOptions"
        @openModal="openVideoModal"
      />
    </div>

    <VideoModal
      :isOpen="isModalOpen"
      :video="selectedVideo"
      :setVideoRef="setVideoRef"
      :playlist="currentPlaylist"
      @close="closeVideoModal"
      @videoPlay="onVideoPlay"
      @videoPause="onVideoPause"
      @videoEnded="onVideoEnded"
      @changeVideo="handleChangeVideo"
    />
  </div>

  <!-- Error message display -->
  <div v-if="error" class="text-center py-4 text-red-500">
    {{ error }}
  </div>

  <!-- Add this near the end of your template -->
  <Teleport to="body">
    <div v-if="showToast" class="toast-message">
      {{ toastMessage }}
    </div>
  </Teleport>
</template>

<script setup>
import {onMounted, onUnmounted, nextTick, inject, provide, computed, ref} from 'vue';
import { useRouter } from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import useVideoOperations from '../composables/useVideoOperations';
import useOptionsMenu from '../composables/useOptionsMenu';
import useToast from '../composables/useToast';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import VideoList from '../components/VideoList.vue';
import VideoModal from '../components/VideoModal.vue';

const router = useRouter();
const emitter = inject('emitter');

const {
  videoContainer,
  videos,
  loading,
  allLoaded,
  error,
  activeTab,
  tabContents,
  tabs,
  tabsWithCounts,
  handleSearch,
  loadMore,
  refreshContent,
  handleScroll,
  scrollToTopAndRefresh,
  observers,
  videoRefs,
  isResetting,
} = useLatestVideos();

const { toastMessage, showToast, displayToast } = useToast();

const {
  playVideo,
  changeVideo,
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
  setVideoRef,
  handleOrientationChange,
  isFullscreen
} = useVideoOperations(videos, videoRefs);

const {
  toggleOptions,
  toggleReadStatus,
  markReadBatch,
  downloadVideo,
  copyVideoLink,
  dislikeVideo,
} = useOptionsMenu(videos, refreshContent);

const filteredVideos = computed(() => {
  const result = {};
  tabs.forEach(tab => {
    result[tab.value] = videos.value[tab.value] || [];
  });
  return result;
});

const isModalOpen = ref(false);
const selectedVideo = ref(null);

const openVideoModal = async (video) => {
  await playVideo(video)
  selectedVideo.value = video;
  isModalOpen.value = true;
};

const closeVideoModal = () => {
  isModalOpen.value = false;
  selectedVideo.value = null;
};

onMounted(() => {
  loadMore();
  window.addEventListener('orientationchange', handleOrientationChange);
  emitter.on('scrollToTopAndRefresh', scrollToTopAndRefresh);
  emitter.on('refreshContent', refreshContent);
  window.history.pushState(null, '', router.currentRoute.value.fullPath);
});

onUnmounted(() => {

  window.removeEventListener('orientationchange', handleOrientationChange);
  emitter.off('scrollToTopAndRefresh', scrollToTopAndRefresh);
  emitter.off('refreshContent', refreshContent);

  // Disconnect all observers
  Object.values(observers.value).forEach(observer => {
    if (observer && typeof observer.disconnect === 'function') {
      observer.disconnect();
    }
  });

  if (videoContainer.value) {
    videoContainer.value.style.overscrollBehavior = 'auto';
  }

  window.onpopstate = null;
});

const goToChannelDetail = (channelId) => {
  router.push({ name: 'ChannelDetail', params: { id: channelId } });
};

provide('videoOperations', {
  setVideoRef,
  goToChannelDetail,
  displayToast,
  isFullscreen,
});

const currentPlaylist = computed(() => {
  return filteredVideos.value[activeTab.value].slice(0, 50);
});

const handleChangeVideo = async (newVideo) => {
  try {
    const updatedVideo = await changeVideo(newVideo);
    if (updatedVideo) {
      selectedVideo.value = updatedVideo;
      await nextTick();
      const videoPlayerComponent = videoRefs.value[updatedVideo.id];
      if (videoPlayerComponent && videoPlayerComponent.play) {
        await videoPlayerComponent.play();
        onVideoPlay(updatedVideo);
      } else {
        console.error('Video player component or play method not found');
      }
    }
  } catch (err) {
    console.error('切换视频失败:', err);
    displayToast('切换视频失败');
  }
};
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

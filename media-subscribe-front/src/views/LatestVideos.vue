<template>
  <div class="latest-videos flex flex-col h-full">
    <SearchBar @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div 
      class="video-container flex-grow relative overflow-hidden"
      ref="videoContainer" 
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
    >
      <div class="tab-content-wrapper">
        <div class="tab-content-inner">
          <div 
            v-for="tab in tabs" 
            :key="tab.value"
            v-show="activeTab === tab.value"
            class="tab-content"
            :ref="el => { if (el) tabContents[tab.value] = el.querySelector('.scroll-content') }"
          >
            <div
              class="scroll-content"
              @scroll="handleScroll"
              :class="{ 'no-scroll': isResetting }"
            >
              <VideoList
                :videos="filteredVideos[tab.value]"
                :loading="loading"
                :setVideoRef="setVideoRef"
                @play="playVideo"
                @videoPlay="onVideoPlay"
                @videoPause="onVideoPause"
                @videoEnded="onVideoEnded"
                @toggleOptions="toggleOptions"
                @goToChannel="goToChannelDetail"
                @videoLeaveViewport="onVideoLeaveViewport"
              />

              <!-- 加载更多指示器 -->
              <div v-if="loading" class="loading-indicator text-center py-4">
                <svg class="animate-spin h-5 w-5 text-gray-500 mx-auto" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p class="mt-2">加载更多...</p>
              </div>

              <!-- 加载完成状态 -->
              <div v-if="allLoaded && !loading" class="text-center py-4">
                <p>没有更多视频了</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 使用 Teleport 将选项框移到 body 下 -->
  <Teleport to="body">
    <OptionsMenu
      v-if="activeOptions !== null"
      :position="optionsPosition"
      :is-read-page="isReadPage"
      :active-tab="activeTab"
      @toggleReadStatus="toggleReadStatus"
      @markReadBatch="markReadBatch"
      @downloadVideo="downloadVideo"
      @copyVideoLink="copyVideoLink"
      @dislikeVideo="dislikeVideo"
      @close="closeOptions"
    />
  </Teleport>

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
import { onMounted, onUnmounted, nextTick, inject, provide, computed } from 'vue';
import { useRouter } from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import useVideoOperations from '../composables/useVideoOperations';
import useOptionsMenu from '../composables/useOptionsMenu';
import useToast from '../composables/useToast';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import VideoList from '../components/VideoList.vue';
import OptionsMenu from '../components/OptionsMenu.vue';

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
  isReadPage,
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
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
  setVideoRef,
  handleOrientationChange,
  onVideoLeaveViewport,
  isFullscreen
} = useVideoOperations(videos, videoRefs);

const {
  activeOptions,
  optionsPosition,
  toggleOptions,
  closeOptions,
  toggleReadStatus,
  markReadBatch,
  downloadVideo,
  copyVideoLink,
  dislikeVideo,
} = useOptionsMenu(videos, refreshContent);

const filteredVideos = computed(() => {
  const result = {};
  tabs.forEach(tab => {
    result[tab.value] = (videos.value[tab.value] || []).filter(video => video && video.id);
  });
  return result;
});


onMounted(() => {
  loadMore();
  window.addEventListener('orientationchange', handleOrientationChange);
  emitter.on('scrollToTopAndRefresh', scrollToTopAndRefresh);
  emitter.on('refreshContent', refreshContent);
  window.history.pushState(null, '', router.currentRoute.value.fullPath);

  nextTick(() => {
    tabs.forEach(tab => {
      if (tabContents.value[tab.value]) {
        tabContents.value[tab.value].addEventListener('scroll', handleScroll);
      } else {
        console.warn('Failed to initialize scroll content for tab:', tab.value);
      }
    });
  });

});

onUnmounted(() => {

  window.removeEventListener('orientationchange', handleOrientationChange);
  emitter.off('scrollToTopAndRefresh', scrollToTopAndRefresh);
  emitter.off('refreshContent', refreshContent);

  tabs.forEach(tab => {
    if (tabContents.value[tab.value]) {
      tabContents.value[tab.value].removeEventListener('scroll', handleScroll);
    }
  });

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
</script>

<style src="./LatestVideos.css" scoped></style>

<style scoped>
/* Add this to your component's styles */

</style>
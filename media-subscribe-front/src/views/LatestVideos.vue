<template>
  <div class="latest-videos bg-gray-100 flex flex-col h-full">
    <SearchBar @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div 
      class="video-container flex-grow relative overflow-hidden"
      ref="videoContainer" 
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
    >
      <div 
        class="refresh-indicator flex items-center justify-center absolute top-0 left-0 right-0 z-10"
        :class="{ 'visible': showRefreshIndicator || isRefreshing }"
        :style="{ height: `${refreshHeight}px` }"
      >
        <svg class="animate-spin h-5 w-5 text-gray-500 mr-2" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="text-gray-600">{{ isRefreshing ? '刷新中' : '下拉刷新' }}</span>
      </div>

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
              class="refresh-wrapper"
              :style="{ transform: `translateY(${refreshHeight}px)` }"
            >
              <div
                class="scroll-content"
                @scroll="handleScroll"
                :class="{ 'no-scroll': isResetting }"
              >
                <TransitionGroup 
                  name="video-list" 
                  tag="div" 
                  class="video-grid sm:grid sm:grid-cols-2 sm:gap-4 p-2"
                >
                  <template v-if="loading && videos[activeTab].length === 0">
                    <div v-for="n in 10" :key="n" class="video-item-placeholder animate-pulse bg-gray-200 h-48"></div>
                  </template>
                  <template v-else>
                    <VideoItem
                      v-for="video in videos[activeTab]"
                      :key="video.id"
                      :video="video"
                      :playbackError="playbackError"
                      @play="playVideo"
                      :setVideoRef="setVideoRef"
                      @videoPlay="onVideoPlay"
                      @videoPause="onVideoPause"
                      @videoEnded="onVideoEnded"
                      @fullscreenChange="onFullscreenChange"
                      @videoMetadataLoaded="onVideoMetadataLoaded"
                      @toggleOptions="toggleOptions"
                      @goToChannel="goToChannelDetail"
                    />
                  </template>
                </TransitionGroup>

                <!-- 加载完成状态 -->
                <div v-if="allLoaded" class="text-center py-4">
                  <p>没有更多视频了</p>
                </div>

                <!-- 添加一个用于触发加载的元素 -->
                <div ref="setLoadTrigger" class="h-1 load-trigger"></div>
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
      @toggleReadStatus="toggleReadStatus"
      @markReadBatch="markReadBatch"
      @downloadVideo="downloadVideo"
      @copyVideoLink="copyVideoLink"
      @dislikeVideo="dislikeVideo"
    />
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, inject, provide, computed } from 'vue';
import { useRouter } from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import useVideoOperations from '../composables/useVideoOperations';
import usePullToRefresh from '../composables/usePullToRefresh';
import useOptionsMenu from '../composables/useOptionsMenu';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import VideoItem from '../components/VideoItem.vue';
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
  videoCounts,
  tabsWithCounts,
  isReadPage,
  handleSearch,
  loadMore,
  refreshContent,
  handleScroll,
  scrollToTopAndRefresh,
  observers,
  videoRefs,
  loadTrigger,
  setLoadTrigger,
  refreshHeight,
  showRefreshIndicator,
  isResetting, // Add this line
} = useLatestVideos();

const {
  playVideo,
  retryPlay,
  playbackError,
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
  onFullscreenChange,
  onVideoMetadataLoaded,
  setVideoRef,  // 确保这里有 setVideoRef
  handleOrientationChange,
} = useVideoOperations(videos, videoRefs);

const activeScrollContent = computed(() => tabContents.value[activeTab.value]);

const {
  handleTouchStart,
  handleTouchMove,
  handleTouchEnd,
  isRefreshing, // 只从 usePullToRefresh 中获取 isRefreshing
} = usePullToRefresh(refreshContent, refreshHeight, showRefreshIndicator, activeScrollContent);

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
} = useOptionsMenu();

const adjustVideoContainerHeight = () => {
  if (videoContainer.value) {
    const windowHeight = window.innerHeight;
    const searchBarHeight = document.querySelector('.search-bar')?.offsetHeight || 0;
    const tabBarHeight = document.querySelector('.custom-tab-bar')?.offsetHeight || 0;
    const newHeight = windowHeight - searchBarHeight - tabBarHeight;
    videoContainer.value.style.height = `${newHeight}px`;
    videoContainer.value.style.maxHeight = `${newHeight}px`;
    videoContainer.value.style.paddingBottom = '1rem';
  }
};

onMounted(() => {
  loadMore();
  window.addEventListener('orientationchange', handleOrientationChange);
  document.addEventListener('click', closeOptions);
  adjustVideoContainerHeight();
  window.addEventListener('resize', adjustVideoContainerHeight);
  emitter.on('scrollToTopAndRefresh', scrollToTopAndRefresh);
  emitter.on('refreshContent', refreshContent);

  if (videoContainer.value) {
    videoContainer.value.style.overscrollBehavior = 'none';
  }

  window.history.pushState(null, '', window.location.href);
  window.onpopstate = function() {
    window.history.pushState(null, '', window.location.href);
  };

  setTimeout(() => {
    if (!loadTrigger.value) {
      const triggerElement = document.querySelector('.load-trigger');
      if (triggerElement) {
        loadTrigger.value = triggerElement;
      } else {
        console.error('Unable to find load trigger element');
      }
    }
  }, 100);

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
  if (videoContainer.value) {
    videoContainer.value.removeEventListener('scroll', handleScroll);
  }
  window.removeEventListener('orientationchange', handleOrientationChange);
  document.removeEventListener('click', closeOptions);
  window.removeEventListener('resize', adjustVideoContainerHeight);
  emitter.off('scrollToTopAndRefresh', scrollToTopAndRefresh);
  emitter.off('refreshContent', refreshContent);

  tabs.forEach(tab => {
    if (tabContents.value[tab.value]) {
      tabContents.value[tab.value].removeEventListener('scroll', handleScroll);
    }
  });

  Object.values(observers.value).forEach(observer => observer.disconnect());

  if (videoContainer.value) {
    videoContainer.value.style.overscrollBehavior = 'auto';
  }

  window.onpopstate = null;
});

const goToChannelDetail = (channelId) => {
  router.push({ name: 'ChannelDetail', params: { id: channelId } });
};

provide('videoOperations', {
  retryPlay,
  setVideoRef,
  goToChannelDetail, // Now we can include this function
});
</script>

<style src="./LatestVideos.css" scoped></style>
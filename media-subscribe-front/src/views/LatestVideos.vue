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
                  <template v-if="isRefreshing">
                    <div v-for="n in 10" :key="`skeleton-${n}`" class="video-item-skeleton bg-white rounded-lg shadow-md p-3 mb-4">
                      <div class="animate-pulse">
                        <div class="bg-gray-300 h-40 w-full rounded-md mb-3"></div>
                        <div class="flex items-center space-x-2 mb-2">
                          <div class="rounded-full bg-gray-300 h-8 w-8"></div>
                          <div class="h-4 bg-gray-300 rounded w-1/2"></div>
                        </div>
                        <div class="space-y-2">
                          <div class="h-4 bg-gray-300 rounded w-3/4"></div>
                          <div class="h-4 bg-gray-300 rounded w-1/2"></div>
                        </div>
                        <div class="mt-2 flex justify-between items-center">
                          <div class="h-3 bg-gray-300 rounded w-1/4"></div>
                          <div class="h-3 bg-gray-300 rounded w-1/4"></div>
                        </div>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <VideoItem
                      v-for="video in filteredVideos"
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
                      @videoEnterViewport="onVideoEnterViewport"
                      @videoLeaveViewport="onVideoLeaveViewport"
                    />
                  </template>
                </TransitionGroup>

                <!-- 加载更多指示器 -->
                <div v-if="loading && !isRefreshing" class="loading-indicator text-center py-4">
                  <svg class="animate-spin h-5 w-5 text-gray-500 mx-auto" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <p class="mt-2">加载更多...</p>
                </div>

                <!-- 加载完成状态 -->
                <div v-if="allLoaded && !loading && !isRefreshing" class="text-center py-4">
                  <p>没有更多视频了</p>
                </div>

                <!-- 添加一个用于触发加载的元素 -->
                <div v-if="!allLoaded && !loading && !isRefreshing" ref="setLoadTrigger" class="h-1 load-trigger"></div>
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

  <!-- Error message display -->
  <div v-if="error" class="text-center py-4 text-red-500">
    {{ error }}
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, inject, provide, computed, watch } from 'vue';
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
  isResetting,
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
  setVideoRef,
  handleOrientationChange,
  pauseVideo, // Add this new method
} = useVideoOperations(videos, videoRefs);

const activeScrollContent = computed(() => tabContents.value[activeTab.value]);

const {
  handleTouchStart: handlePullToRefreshTouchStart,
  handleTouchMove: handlePullToRefreshTouchMove,
  handleTouchEnd: handlePullToRefreshTouchEnd,
  isRefreshing,
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

const filteredVideos = computed(() => {
  return (videos.value[activeTab.value] || []).filter(video => video && video.id);
});

const onVideoEnterViewport = (video) => {
  console.log(`Video ${video.id} entered viewport`);
  // 如果需要，可以在这里添加自动播放逻辑
};

const onVideoLeaveViewport = (video) => {
  console.log(`Video ${video.id} left viewport`);
  pauseVideo(video);
};

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

const preventGoBack = (event) => {
  event.preventDefault();
  window.history.pushState(null, '', router.currentRoute.value.fullPath);
};

const touchStartX = ref(0);
const touchEndX = ref(0);

const handleTouchStart = (event) => {
  touchStartX.value = event.touches[0].clientX;
};

const handleTouchMove = (event) => {
  touchEndX.value = event.touches[0].clientX;
};

const handleTouchEnd = () => {
  const swipeThreshold = 100; // 最小滑动距离
  const swipeDistance = touchEndX.value - touchStartX.value;

  if (Math.abs(swipeDistance) > swipeThreshold) {
    const currentIndex = tabs.findIndex(tab => tab.value === activeTab.value);
    if (swipeDistance > 0 && currentIndex > 0) {
      // 向右滑动，切换到上一个标签
      activeTab.value = tabs[currentIndex - 1].value;
    } else if (swipeDistance < 0 && currentIndex < tabs.length - 1) {
      // 向左滑动，切换到下一个标签
      activeTab.value = tabs[currentIndex + 1].value;
    }
  }

  // 重置触摸位置
  touchStartX.value = 0;
  touchEndX.value = 0;
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
    videoContainer.value.addEventListener('touchstart', handleTouchStart);
    videoContainer.value.addEventListener('touchmove', handleTouchMove);
    videoContainer.value.addEventListener('touchend', handleTouchEnd);
  }

  window.history.pushState(null, '', router.currentRoute.value.fullPath);
  window.addEventListener('popstate', preventGoBack);

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
    videoContainer.value.removeEventListener('touchstart', handleTouchStart);
    videoContainer.value.removeEventListener('touchmove', handleTouchMove);
    videoContainer.value.removeEventListener('touchend', handleTouchEnd);
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
  retryPlay,
  setVideoRef,
  goToChannelDetail,
});
</script>

<style src="./LatestVideos.css" scoped></style>
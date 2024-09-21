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
                @scroll="handleScroll($event, channelId)"
                :class="{ 'no-scroll': isResetting }"
              >
                <VideoList
                  :show-avatar="showAvatar"
                  :videos="filteredVideos[tab.value]"
                  :loading="loading && !isRefreshing"
                  :playbackError="playbackError"
                  :setVideoRef="setVideoRef"
                  @play="playVideo"
                  @videoPlay="onVideoPlay"
                  @videoPause="onVideoPause"
                  @videoEnded="onVideoEnded"
                  @toggleOptions="toggleOptions"
                  @goToChannel="goToChannelDetail"
                  @videoEnterViewport="onVideoEnterViewport"
                  @videoLeaveViewport="onVideoLeaveViewport"
                />

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
import { ref, onMounted, onUnmounted, nextTick, inject, provide, computed } from 'vue';
import {useRoute, useRouter} from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import useVideoOperations from '../composables/useVideoOperations';
import usePullToRefresh from '../composables/usePullToRefresh';
import useOptionsMenu from '../composables/useOptionsMenu';
import useToast from '../composables/useToast';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import VideoList from '../components/VideoList.vue';
import OptionsMenu from '../components/OptionsMenu.vue';

const router = useRouter();
const route = useRoute();
const channelId = route.params.id;

const emitter = inject('emitter');
const showAvatar = ref(false);
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
  refreshHeight,
  showRefreshIndicator,
  isResetting,
} = useLatestVideos();

const { toastMessage, showToast, displayToast } = useToast();

const {
  playVideo,
  retryPlay,
  playbackError,
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
  // onFullscreenChange,
  // onVideoMetadataLoaded,
  setVideoRef,
  handleOrientationChange,
  pauseVideo,
  attemptAutoplay,
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
} = useOptionsMenu(videos, refreshContent);

const filteredVideos = computed(() => {
  const result = {};
  tabs.forEach(tab => {
    result[tab.value] = (videos.value[tab.value] || []).filter(video => video && video.id);
  });
  return result;
});

const onVideoEnterViewport = (video) => {
  // 如果需要，可以在这里添加自动播放逻辑
};

const onVideoLeaveViewport = (video) => {
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
const touchStartY = ref(0);
const touchEndX = ref(0);
const touchEndY = ref(0);
const isHorizontalSwipe = ref(false);

const handleTouchStart = (event) => {
  touchStartX.value = event.touches[0].clientX;
  touchStartY.value = event.touches[0].clientY;
  isHorizontalSwipe.value = false;
  handlePullToRefreshTouchStart(event);
};

const handleTouchMove = (event) => {
  touchEndX.value = event.touches[0].clientX;
  touchEndY.value = event.touches[0].clientY;

  const deltaX = Math.abs(touchEndX.value - touchStartX.value);
  const deltaY = Math.abs(touchEndY.value - touchStartY.value);
  // 如果水平移动距离大于垂直移动距离，且大于一定阈值，则认为是水平滑动
  if (deltaX > deltaY && deltaX > 10) {
    isHorizontalSwipe.value = true;
  }

  // 只有在不是水平滑动的情况下，才触发下拉刷新的移动事件
  if (!isHorizontalSwipe.value) {
    handlePullToRefreshTouchMove(event);
  }
};

const handleTouchEnd = (event) => {
  const swipeThreshold = 50; // 最小滑动距离
  const swipeDistanceX = touchEndX.value - touchStartX.value;
  const swipeDistanceY = touchEndY.value - touchStartY.value;

  if (isHorizontalSwipe.value) {
    if (Math.abs(swipeDistanceX) > swipeThreshold) {
      const currentIndex = tabs.findIndex(tab => tab.value === activeTab.value);
      if (swipeDistanceX > 0 && currentIndex > 0) {
        // 向右滑动，切换到上一个标签
        activeTab.value = tabs[currentIndex - 1].value;
      } else if (swipeDistanceX < 0 && currentIndex < tabs.length - 1) {
        // 向左滑动，切换到下一个标签
        activeTab.value = tabs[currentIndex + 1].value;
      }
    }
  } else {
    handlePullToRefreshTouchEnd(event);
  }

  // 重置触摸位置
  touchStartX.value = 0;
  touchStartY.value = 0;
  touchEndX.value = 0;
  touchEndY.value = 0;
};

onMounted(() => {
  loadMore(channelId);
  window.addEventListener('orientationchange', handleOrientationChange);
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
  displayToast,
  attemptAutoplay,
});
</script>

<style src="./LatestVideos.css" scoped></style>

<style scoped>
/* Add this to your component's styles */

</style>
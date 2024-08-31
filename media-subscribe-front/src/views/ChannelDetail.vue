<template>
  <div class="channel-detail bg-gray-100 min-h-screen">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 w-full flex-grow flex flex-col">
      <!-- 搜索栏 -->
      <div class="search-bar sticky top-0 bg-white z-10 p-4 shadow-sm">
        <div class="flex items-center max-w-3xl mx-auto relative">
          <input 
            v-model="searchQuery" 
            @keyup.enter="handleSearchClick"
            type="text" 
            placeholder="搜索视频..." 
            class="flex-grow h-8 px-4 pr-10 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200"
          >
          <button 
            v-if="searchQuery"
            @click="clearSearch"
            class="absolute right-20 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </button>
          <button 
            @click="handleSearchClick"
            class="h-8 px-6 text-sm font-medium bg-blue-500 text-white rounded-r-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-50 focus:ring-offset-2 transition duration-200"
          >
            搜索
          </button>
        </div>
      </div>

      <div class="video-container" ref="videoContainer" @scroll="handleScroll">
        <div 
          v-for="video in videos" 
          :key="video.id" 
          class="video-item bg-white shadow-sm rounded-lg overflow-hidden mb-4"
        >
          <div class="video-thumbnail relative">
            <img 
              v-if="!video.isPlaying" 
              :src="video.thumbnail" 
              referrerpolicy="no-referrer" 
              alt="Video thumbnail" 
              class="w-full h-full object-cover"
              @click="toggleVideoPlay(video)"
            >
            <video
              v-show="video.isPlaying"
              :src="video.video_url"
              :ref="el => { if (el) videoRefs[video.id] = el }"
              class="absolute top-0 left-0 w-full h-full object-cover"
              controls
              @play="onVideoPlay(video)"
              @pause="onVideoPause(video)"
              @ended="onVideoEnded(video)"
            ></video>
            <div v-if="!video.isPlaying" class="video-duration">{{ formatDuration(video.duration) }}</div>
            <div v-if="!video.isPlaying" class="play-button" @click="toggleVideoPlay(video)">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12">
                <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clip-rule="evenodd" />
              </svg>
            </div>
          </div>
          <div class="video-info p-3 flex flex-col">
            <div class="flex justify-between items-start">
              <h2 class="video-title text-base font-semibold text-gray-900 line-clamp-2 flex-grow pr-2">{{ video.title }}</h2>
              <div class="video-meta text-xs text-gray-500 whitespace-nowrap">
                <span>{{ formatDate(video.uploaded_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-4">
          <p>加载中...</p>
        </div>

        <!-- 加载完成状态 -->
        <div v-if="allLoaded" class="text-center py-4">
          <p>没有更多视频了</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
const route = useRoute();
const channelId = route.params.id;
import axios from '../utils/axios';

const channelInfo = ref({});
const latestVideos = ref(null);
const videoContainer = ref(null);
const videos = ref([]);
const error = ref(null);
const currentPage = ref(1);
const searchQuery = ref('');
const videoRefs = ref({});
const loading = ref(false);
const allLoaded = ref(false);
const scrollPosition = ref(0);
const isLoadingMore = ref(false);

const saveScrollPosition = () => {
  if (videoContainer.value) {
    scrollPosition.value = videoContainer.value.scrollTop;
  }
};

const restoreScrollPosition = () => {
  if (videoContainer.value && scrollPosition.value > 0) {
    nextTick(() => {
      videoContainer.value.scrollTop = scrollPosition.value;
    });
  }
};

const loadMore = async () => {
  if (loading.value || allLoaded.value || isLoadingMore.value) return;
  isLoadingMore.value = true;
  loading.value = true;
  try {
    const response = await axios.get('/api/channel-video/list', {
      params: {
        page: currentPage.value,
        pageSize: 10,
        channel_id: channelId,
        query: searchQuery.value
      }
    });
    if (response.data.code === 0) {
      const newVideos = response.data.data.data.map(video => ({
        ...video,
        isPlaying: false,
        video_url: null
      }));
      if (newVideos.length) {
        videos.value = [...videos.value, ...newVideos];
        currentPage.value++;
      } else {
        allLoaded.value = true;
      }
    } else {
      throw new Error(response.data.msg || '获取视频列表失败');
    }
  } catch (err) {
    console.error('获取视频列表失败:', err);
    error.value = err.message || '获取视频列表失败';
  } finally {
    loading.value = false;
    isLoadingMore.value = false;
    nextTick(() => {
      restoreScrollPosition();
    });
  }
};

const handleScroll = () => {
  if (videoContainer.value) {
    const { scrollTop, scrollHeight, clientHeight } = videoContainer.value;
    if (scrollTop + clientHeight >= scrollHeight - 100 && !isLoadingMore.value) {
      loadMore();
    }
    saveScrollPosition();
  }
};

const handleSearchClick = () => {
  videos.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  error.value = null;
  scrollPosition.value = 0;
  loadMore();
};

const clearSearch = () => {
  searchQuery.value = '';
  handleSearchClick();
};

const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now - date);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 1) return '昨天';
  if (diffDays <= 7) return `${diffDays}天前`;
  return date.toLocaleDateString('zh-CN');
};

const formatViews = (views) => {
  if (views < 1000) return views;
  if (views < 1000000) return `${(views / 1000).toFixed(1)}K`;
  return `${(views / 1000000).toFixed(1)}M`;
};

const toggleVideoPlay = async (video) => {
  videos.value.forEach(v => {
    if (v.isPlaying && v !== video) {
      v.isPlaying = false;
      const videoElement = videoRefs.value[v.id];
      if (videoElement) {
        videoElement.pause();
        videoElement.currentTime = 0;
      }
    }
  });

  video.isPlaying = !video.isPlaying;

  if (video.isPlaying && !video.video_url) {
    try {
      const response = await axios.get('/api/channel-video/video/url', {
        params: {
          channel_id: video.channel_id,
          video_id: video.video_id
        }
      });
      if (response.data.code === 0) {
        video.video_url = response.data.data;
        await nextTick();
        const videoElement = videoRefs.value[video.id];
        if (videoElement) {
          videoElement.play();
        }
      } else {
        throw new Error(response.data.msg || '获取视频地址失败');
      }
    } catch (err) {
      console.error('获取视频地址失败:', err);
      video.isPlaying = false;
      error.value = err.message || '获取视频地址失败，请稍后重试';
    }
  } else if (video.isPlaying) {
    const videoElement = videoRefs.value[video.id];
    if (videoElement) {
      videoElement.play();
    }
  } else {
    const videoElement = videoRefs.value[video.id];
    if (videoElement) {
      videoElement.pause();
    }
  }
};

const onVideoPlay = (video) => {
  video.isPlaying = true;
  setupIntersectionObserver(video);
};

const onVideoPause = (video) => {
  video.isPlaying = false;
};

const onVideoEnded = (video) => {
  video.isPlaying = false;
};

const setupIntersectionObserver = (video) => {
  const videoElement = videoRefs.value[video.id];
  if (!videoElement) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting && !videoElement.paused) {
        videoElement.pause();
        video.isPlaying = false;
      }
    });
  }, {
    threshold: 0.5
  });

  observer.observe(videoElement);

  videoElement.addEventListener('pause', () => observer.disconnect());
  videoElement.addEventListener('ended', () => observer.disconnect());
};

watch(videos, () => {
  nextTick(() => {
    restoreScrollPosition();
  });
}, { deep: true });

onMounted(() => {
  loadMore();
});

onUnmounted(() => {
  if (videoContainer.value) {
    videoContainer.value.removeEventListener('scroll', saveScrollPosition);
  }
});
</script>

<style scoped>
.channel-detail {
  @apply pb-4 min-h-full;
}

.video-container {
  height: calc(100vh - 130px); /* 适用于移动端 */
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* Internet Explorer 10+ */
}

@media (min-width: 768px) {
  .video-container {
    height: calc(100vh - 90px); /* 适用于桌面端 */
  }
}

.video-container::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none; /* Chrome, Safari, Opera */
}

.video-item {
  @apply mt-3;
}

.video-thumbnail {
  @apply relative pt-[56.25%] cursor-pointer;
  height: 0;
}

.video-thumbnail img,
.video-thumbnail video {
  @apply absolute top-0 left-0 w-full h-full object-cover;
}

.video-duration {
  @apply absolute bottom-2 right-2 bg-black bg-opacity-80 text-white text-xs px-1 py-0.5 rounded;
}

.video-title {
  @apply line-clamp-2 leading-tight;
}

.video-meta {
  @apply mt-1 flex items-center;
}

.play-button {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white opacity-80;
}

.video-thumbnail:hover .play-button {
  @apply opacity-100;
}

.search-bar {
  background-color: white;
  z-index: 10;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.search-bar input {
  border-right: none;
}

.search-bar button {
  border-left: none;
}

.search-bar input:focus,
.search-bar button:focus {
  box-shadow: 0 0 0 0 rgba(111, 164, 248, 0.5);
}

@media (min-width: 640px) {
  .video-item {
    @apply flex;
  }

  .video-thumbnail {
    @apply w-1/2 pt-[28.125%];
  }

  .video-info {
    @apply w-1/2 flex flex-col justify-between p-3;
  }
}

.video-info {
  @apply flex flex-col;
}

.video-title {
  @apply line-clamp-2 leading-tight;
}

.video-meta {
  @apply text-right flex-shrink-0;
}

@media (min-width: 640px) {
  .video-item {
    @apply flex;
  }

  .video-thumbnail {
    @apply w-1/2 pt-[28.125%];
  }

  .video-info {
    @apply w-1/2 flex flex-col justify-between p-3;
  }
}
</style>
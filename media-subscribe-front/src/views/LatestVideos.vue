<template>
  <div ref="latestVideos" class="latest-videos">
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

    <div v-if="loading" class="text-center">
      <p>加载中...</p>
    </div>
    <div v-else-if="error" class="text-center text-red-500">
      <p>{{ error }}</p>
    </div>
    <div v-else class="video-list space-y-4">
      <div 
        v-for="video in videos" 
        :key="video.id" 
        class="video-item bg-white shadow-sm"
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
        <div class="video-info p-3">
          <h2 class="video-title text-base font-semibold text-gray-900 line-clamp-2">{{ video.title }}</h2>
          <p class="video-channel text-sm text-gray-600 mt-1">{{ video.channel_name }}</p>
          <div class="video-meta text-xs text-gray-500 mt-1">
            <span>{{ formatViews(video.views) }} 次观看</span>
            <span class="mx-1">•</span>
            <span>{{ formatDate(video.uploaded_at) }}</span>
          </div>
        </div>
      </div>
    </div>
    <infinite-loading :distance="10" @infinite="infiniteHandler">
      <template #loading>
        <div class="text-center">加载中...</div>
      </template>
      <template #complete>
        <div class="text-center">没有更多视频了</div>
      </template>
      <template #error>
        <div class="text-center">加载失败，请重试</div>
      </template>
    </infinite-loading>
  </div>
</template>

<script setup>
import axios from '../utils/axios';
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import InfiniteLoading from 'v3-infinite-loading';

const videos = ref([]);
const error = ref(null);
const currentPage = ref(1);
const searchQuery = ref('');
const videoRefs = ref({});
const loading = ref(false);

const infiniteHandler = async ($state) => {
  if (loading.value) return;
  loading.value = true;
  try {
    const response = await axios.get('/api/channel-video/list', {
      params: {
        page: currentPage.value,
        pageSize: 10,
        query: searchQuery.value
      }
    });
    if (response.data.code === 0) {
      const newVideos = response.data.data.data.map(video => ({
        ...video,
        isPlaying: false,
        video_url: null // 初始化 video_url 为 null
      }));
      if (newVideos.length) {
        videos.value = [...videos.value, ...newVideos];
        currentPage.value++;
        $state.loaded();
      } else {
        $state.complete();
      }
    } else {
      throw new Error(response.data.msg || '获取视频列表失败');
    }
  } catch (err) {
    if (axios.isCancel(err)) {
      console.log('请求被取消', err.message);
    } else {
      console.error('获取视频列表失败:', err);
      error.value = err.message || '获取视频列表失败';
    }
    $state.error();
  } finally {
    loading.value = false;
  }
};

function onCanPlay(event) {
  console.log(event);
}

const handleSearchClick = () => {
  videos.value = [];
  currentPage.value = 1;
  error.value = null;
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

// 添加一个新的格式化函数用于显示观看次数
const formatViews = (views) => {
  if (views < 1000) return views;
  if (views < 1000000) return `${(views / 1000).toFixed(1)}K`;
  return `${(views / 1000000).toFixed(1)}M`;
};

const toggleVideoPlay = async (video) => {
  // 停止所有正在播放的视频
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
  
  // 切换当前视频的播放状态
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
        // 确保 DOM 更新后再播放视频
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
    // 如果视频 URL 已存在，直接播放
    const videoElement = videoRefs.value[video.id];
    if (videoElement) {
      videoElement.play();
    }
  } else {
    // 如果是暂停状态，暂停视频
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
    threshold: 0.5 // 当视频有一半不可见时触发
  });

  observer.observe(videoElement);

  // 在视频暂停或结束时取消观察
  videoElement.addEventListener('pause', () => observer.disconnect());
  videoElement.addEventListener('ended', () => observer.disconnect());
};

</script>

<style scoped>
.latest-videos {
  @apply pb-4 min-h-full bg-gray-100;
}

.search-bar {
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 10;
  padding: 1rem;
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

.video-list {
  @apply px-4;
}

.video-item {
  @apply mb-4 rounded-lg overflow-hidden;
}

.video-thumbnail {
  @apply relative pt-[56.25%] cursor-pointer;
  height: 0; /* 确保容器高度由 padding-top 控制 */
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

.video-channel {
  @apply mt-1;
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

/* 移除之前的 .line-clamp-2 类，因为我们现在直接在 .video-title 中使用它 */

</style>
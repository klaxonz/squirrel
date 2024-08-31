<template>
    <div class="latest-videos bg-gray-100 min-h-screen flex flex-col">
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
  
        <div class="video-container flex-grow overflow-y-auto" ref="videoContainer" @scroll="handleScroll">
          <div 
            v-for="video in videos" 
            :key="video.id" 
            class="video-item bg-white shadow-sm rounded-lg overflow-hidden mb-4"
          >
            <div class="video-thumbnail relative cursor-pointer">
              <img 
                v-if="!video.isPlaying" 
                :src="video.thumbnail" 
                referrerpolicy="no-referrer" 
                alt="Video thumbnail" 
                class="w-full h-full object-cover"
                @click="playVideo(video)"
              >
              <div v-show="video.isPlaying" class="video-wrapper">
                <video
                  :src="video.video_url"
                  :ref="el => { if (el) videoRefs[video.id] = el }"
                  class="video-player"
                  controls
                  @play="onVideoPlay(video)"
                  @pause="onVideoPause(video)"
                  @ended="onVideoEnded(video)"
                  @fullscreenchange="onFullscreenChange"
                ></video>
              </div>
              <div v-if="!video.isPlaying" class="video-duration">{{ formatDuration(video.duration) }}</div>
              <div v-if="!video.isPlaying" class="play-button" @click="playVideo(video)">
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
  
          <!-- 添加一个用于触发加载的元素 -->
          <div ref="loadTrigger" class="h-1"></div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onUnmounted, nextTick } from 'vue';
  import { useRoute } from 'vue-router';
  import axios from '../utils/axios';

  const route = useRoute();
  const channelId = route.params.id;
  
  const videoContainer = ref(null);
  const loadTrigger = ref(null);
  const videos = ref([]);
  const currentPage = ref(1);
  const loading = ref(false);
  const allLoaded = ref(false);
  const error = ref(null);
  const searchQuery = ref('');
  const videoRefs = ref({});
  
  const handleScroll = () => {
    if (loadTrigger.value && videoContainer.value) {
      const containerRect = videoContainer.value.getBoundingClientRect();
      const triggerRect = loadTrigger.value.getBoundingClientRect();
      
      if (triggerRect.top <= containerRect.bottom + 100) {
        console.log('Trigger element is visible, loading more...'); // 调试信息
        loadMore();
      }
    }
  };
  
  const loadMore = async () => {
    if (loading.value || allLoaded.value) {
      console.log('Already loading or all loaded, skipping...'); // 调试信息
      return;
    }
    
    console.log('Loading more videos...'); // 调试信息
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
      console.log('API response:', response.data); // 调试信息
      if (response.data.code === 0) {
        const newVideos = response.data.data.data.map(video => ({
          ...video,
          isPlaying: false,
          video_url: null
        }));
        if (newVideos.length === 0) {
          console.log('No more videos to load'); // 调试信息
          allLoaded.value = true;
        } else {
          videos.value.push(...newVideos);
          currentPage.value++;
          console.log('New videos added, total count:', videos.value.length); // 调试信息
        }
      } else {
        throw new Error(response.data.msg || '获取视频列表失败');
      }
    } catch (err) {
      console.error('获取视频列表失败:', err);
      error.value = err.message || '获取视频列表失败';
    } finally {
      loading.value = false;
    }
  };
  
  const handleSearchClick = () => {
    videos.value = [];
    currentPage.value = 1;
    allLoaded.value = false;
    error.value = null;
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
    if (diffDays <= 30) return `${Math.floor(diffDays / 7)}周前`;
    if (diffDays <= 365) return `${Math.floor(diffDays / 30)}个月前`;
    return `${Math.floor(diffDays / 365)}年前`;
  };
  
  const playVideo = async (video) => {
    if (!video.video_url) {
      try {
        const response = await axios.get('/api/channel-video/video/url', {
          params: {
            channel_id: video.channel_id,
            video_id: video.video_id
          }
        });
        if (response.data.code === 0) {
          video.video_url = response.data.data;
        } else {
          throw new Error(response.data.msg || '获取视频地址失败');
        }
      } catch (err) {
        console.error('获取视频地址失败:', err);
        return;
      }
    }
    
    video.isPlaying = true;
    
    // 停止其他正在播放的视频
    videos.value.forEach(v => {
      if (v !== video && v.isPlaying) {
        v.isPlaying = false;
        const videoElement = videoRefs.value[v.id];
        if (videoElement) {
          videoElement.pause();
        }
      }
    });
  
    // 等待 DOM 更新后播放视频
    await nextTick();
    const videoElement = videoRefs.value[video.id];
    if (videoElement) {
      try {
        await videoElement.play();
      } catch (error) {
        console.error('自动播放失败:', error);
        // 如果自动播放失败，可能是因为浏览器策略，我们保持 isPlaying 为 true，让用户手动点击播放
      }
    }
  };
  
  const onVideoPlay = (video) => {
    video.isPlaying = true;
  };
  
  const onVideoPause = (video) => {
    // 不要在这里设置 isPlaying 为 false，让用户可以暂停后继续播放
  };
  
  const onVideoEnded = (video) => {
    video.isPlaying = false;
  };
  
  const onFullscreenChange = (event) => {
    const videoElement = event.target;
    if (document.fullscreenElement) {
      // 进入全屏
      if (window.screen.orientation.type.includes('portrait')) {
        videoElement.style.objectFit = 'contain';
      } else {
        videoElement.style.objectFit = 'cover';
      }
    } else {
      // 退出全屏
      videoElement.style.objectFit = 'cover';
    }
  };
  
  const goToChannelDetail = (channelId) => {
    router.push({ name: 'ChannelDetail', params: { id: channelId } });
  };
  
  onMounted(() => {
    console.log('Component mounted, loading initial videos...'); // 调试信息
    loadMore();
    if (videoContainer.value) {
      videoContainer.value.addEventListener('scroll', handleScroll);
    }
    window.addEventListener('orientationchange', handleOrientationChange);
  });
  
  onUnmounted(() => {
    if (videoContainer.value) {
      videoContainer.value.removeEventListener('scroll', handleScroll);
    }
    window.removeEventListener('orientationchange', handleOrientationChange);
  });
  
  const handleOrientationChange = () => {
    videos.value.forEach(video => {
      if (video.isPlaying) {
        const videoElement = videoRefs.value[video.id];
        if (videoElement && document.fullscreenElement) {
          if (window.screen.orientation.type.includes('portrait')) {
            videoElement.style.objectFit = 'contain';
          } else {
            videoElement.style.objectFit = 'cover';
          }
        }
      }
    });
  };
  </script>
  
  <style scoped>
  .latest-videos {
    @apply min-h-full;
  }
  
  .video-container {
    height: calc(100vh - 130px); /* 120px (搜索栏) + 56px (底部导航栏) */
    overflow-y: auto;
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* Internet Explorer 10+ */
  }
  
  @media (min-width: 768px) {
    .video-container {
      height: calc(100vh - 90px); /* 只考虑搜索栏的高度，因为导航栏在侧边 */
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
  
  .video-wrapper {
    @apply absolute top-0 left-0 w-full h-full;
  }
  
  .video-player {
    @apply absolute top-0 left-0 w-full h-full object-cover;
  }
  
  .video-thumbnail img {
    @apply absolute top-0 left-0 w-full h-full object-cover;
  }
  
  .video-duration {
    @apply absolute bottom-2 right-2 bg-black bg-opacity-80 text-white text-xs px-1 py-0.5 rounded;
  }
  
  .video-title {
    @apply line-clamp-2 leading-tight mb-2;
  }
  
  .video-channel {
    @apply truncate hover:text-blue-500 transition-colors duration-200;
  }
  
  .video-meta {
    @apply text-right;
  }
  
  .play-button {
    @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white opacity-80 cursor-pointer;
  }
  
  .video-thumbnail:hover .play-button {
    @apply opacity-100;
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
  
  /* 确保视频控件在全屏模式下可见 */
  .video-player::-webkit-media-controls {
    display: flex !important;
    visibility: visible !important;
  }
  </style>
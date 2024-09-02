<template>
  <div class="latest-videos bg-gray-100 min-h-screen flex flex-col">
    <div class="max-w-4xl mx-auto sm:px-6 lg:px-8 w-full flex-grow flex flex-col">
      <!-- 搜索栏 -->
      <div :class="['search-bar', { 'hidden': isScrollingUp }]" ref="searchBar">
        <div class="flex items-center max-w-3xl mx-auto relative">
          <input
              v-model="searchQuery"
              @keyup.enter="handleSearchClick"
              type="text"
              placeholder="搜索视频..."
              class="search-input flex-grow h-8 px-4 pr-10 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200"
          >
          <button
              v-if="searchQuery"
              @click="clearSearch"
              class="clear-button absolute right-20 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clip-rule="evenodd"/>
            </svg>
          </button>
          <button
              @click="handleSearchClick"
              class="search-button h-8 px-4 text-sm font-medium bg-blue-500 text-white rounded-r-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-50 focus:ring-offset-2 transition duration-200"
          >
            搜索
          </button>
        </div>
      </div>

      <div class="video-container flex-grow overflow-y-auto" ref="videoContainer" @scroll="handleScroll">
        <div
            v-for="video in videos"
            :key="video.id"
            class="video-item lg:mt-3 lg:rounded-lg bg-white shadow-sm overflow-hidden relative"
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
                <path fill-rule="evenodd"
                      d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z"
                      clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
          <div class="video-info p-3 flex flex-col">
            <div class="flex justify-between items-start">
              <a
                  :href="video.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="video-title text-base font-semibold text-gray-900 hover:text-blue-600 transition-colors duration-200 line-clamp-2 flex-grow pr-2"
              >
                {{ video.title }}
              </a>
              <div class="flex-shrink-0 relative">
                <button @click="toggleOptions(video.id, $event)"
                        class="text-gray-500 hover:text-gray-700 focus:outline-none p-1">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                        d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"/>
                  </svg>
                </button>
              </div>
            </div>
            <div class="flex justify-between items-center mt-2">
              <div class="flex items-center cursor-pointer" @click="goToChannelDetail(video.channel_id)">
                <img
                    :src="video.channel_avatar"
                    :alt="video.channel_name"
                    class="w-6 h-6 rounded-full mr-2"
                    referrerpolicy="no-referrer"
                >
                <p class="video-channel text-sm text-gray-600 truncate hover:text-blue-500 transition-colors duration-200">
                  {{ video.channel_name }}</p>
              </div>
              <span class="text-xs text-gray-500 whitespace-nowrap">{{ formatDate(video.uploaded_at) }}</span>
            </div>
            <!-- 添加下载标识 -->
            <div v-if="video.if_downloaded" class="downloaded-badge mt-2 text-green-500 text-xs">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block mr-1" viewBox="0 0 20 20"
                   fill="currentColor">
                <path fill-rule="evenodd"
                      d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                      clip-rule="evenodd"/>
              </svg>
              已下载
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

  <!-- 使用 Teleport 将选项框移到 body 下 -->
  <Teleport to="body">
    <div
        v-if="activeOptions !== null"
        class="absolute bg-white shadow-lg rounded-md py-2 z-50 w-32"
        :style="{ top: optionsPosition.top + 'px', left: optionsPosition.left + 'px' }"
        @click.stop
    >
      <button @click="downloadVideo" class="block w-full text-left px-4 py-2 hover:bg-gray-100 text-sm">下载</button>
      <button @click="copyVideoLink" class="block w-full text-left px-4 py-2 hover:bg-gray-100 text-sm">复制链接
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from '../utils/axios';

const router = useRouter();

const videoContainer = ref(null);
const loadTrigger = ref(null);
const videos = ref([]);
const currentPage = ref(1);
const loading = ref(false);
const allLoaded = ref(false);
const error = ref(null);
const searchQuery = ref('');
const videoRefs = ref({});
const activeOptions = ref(null);
const optionsPosition = ref({ top: 0, left: 0 });
const activeVideo = ref(null);
const isScrollingUp = ref(false);
let lastScrollTop = 0;

const handleScroll = () => {
  if (loadTrigger.value && videoContainer.value) {
    const containerRect = videoContainer.value.getBoundingClientRect();
    const triggerRect = loadTrigger.value.getBoundingClientRect();

    if (triggerRect.top <= containerRect.bottom + 100) {
      console.log('Trigger element is visible, loading more...'); // 调试信息
      loadMore();
    }

    const scrollTop = videoContainer.value.scrollTop;
    isScrollingUp.value = scrollTop < lastScrollTop;
    lastScrollTop = scrollTop <= 0 ? 0 : scrollTop; // For Mobile or negative scrolling
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
      if (video.if_downloaded) {
        video.video_url = '/api/channel/video/play/'+ video.channel_id + '/' + video.video_id;
      } else {
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
      }

    } catch (err) {
      console.error('获取视频地址失败:', err);
      showToast('获取视频地址失败: ' + (err.message || '未知错误'), true);
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
      showToast('自动播放失败，请手动点击播放按钮', true);
      // 如果自动播放失败，可能是因为浏览器策略，我们保持 isPlaying 为 true，让用户手动点击播放按钮
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
  router.push({name: 'ChannelDetail', params: {id: channelId}});
};

const toggleOptions = (videoId, event) => {
  event.stopPropagation();
  if (activeOptions.value === videoId) {
    closeOptions();
  } else {
    activeOptions.value = videoId;
    activeVideo.value = videos.value.find(v => v.id === videoId);
    nextTick(() => {
      const button = event.target.closest('button');
      const rect = button.getBoundingClientRect();
      optionsPosition.value = {
        top: rect.bottom + window.scrollY,
        left: Math.min(rect.left, window.innerWidth - 128) // 128px 是选项框的宽度
      };
    });
  }
};

const closeOptions = () => {
  activeOptions.value = null;
  activeVideo.value = null;
};

const showToast = (message, isError = false) => {
  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.position = 'fixed';
  toast.style.bottom = '20px';
  toast.style.left = '50%';
  toast.style.transform = 'translateX(-50%)';
  toast.style.padding = '10px 20px';
  toast.style.borderRadius = '4px';
  toast.style.color = 'white';
  toast.style.backgroundColor = isError ? '#f56c6c' : '#67c23a';
  toast.style.zIndex = '9999';

  document.body.appendChild(toast);

  setTimeout(() => {
    document.body.removeChild(toast);
  }, 3000);
};

const downloadVideo = async () => {
  if (activeVideo.value) {
    try {
      const response = await axios.post('/api/channel-video/download', {
        channel_id: activeVideo.value.channel_id,
        video_id: activeVideo.value.video_id
      });

      if (response.data.code === 0) {
        showToast('视频下载已开始，请稍后查看下载列表');
        // 更新视频的下载状态
        activeVideo.value.if_downloaded = true;
      } else {
        throw new Error(response.data.msg || '下载视频失败');
      }
    } catch (error) {
      console.error('下载视频失败:', error);
      showToast('下载视频失败: ' + (error.message || '未知错误'), true);
    }
  }
  closeOptions();
};

const copyVideoLink = () => {
  if (activeVideo.value) {
    navigator.clipboard.writeText(activeVideo.value.url).then(() => {
      console.log('Video link copied to clipboard');
      // 可以添加一个提示，告诉用户链接已复制
    }).catch(err => {
      console.error('Failed to copy link: ', err);
    });
  }
  closeOptions();
};

// 点击外部关闭选项框
const closeOptionsOnOutsideClick = (event) => {
  if (activeOptions.value && !event.target.closest('.video-item')) {
    activeOptions.value = null;
  }
};

onMounted(() => {
  console.log('Component mounted, loading initial videos...'); // 调试信息
  loadMore();
  if (videoContainer.value) {
    videoContainer.value.addEventListener('scroll', handleScroll);
  }
  window.addEventListener('orientationchange', handleOrientationChange);
  document.addEventListener('click', closeOptionsOnOutsideClick);
  document.addEventListener('click', closeOptions);
});

onUnmounted(() => {
  if (videoContainer.value) {
    videoContainer.value.removeEventListener('scroll', handleScroll);
  }
  window.removeEventListener('orientationchange', handleOrientationChange);
  document.removeEventListener('click', closeOptionsOnOutsideClick);
  document.removeEventListener('click', closeOptions);
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

.search-bar {
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 10;
  padding: 0.5rem; /* Reduced padding */
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease-in-out;
}

.search-bar.hidden {
  transform: translateY(-100%);
}

.search-input {
  border-right: none;
  border-radius: 9999px 0 0 9999px; /* Rounded left corners */
}

.clear-button {
  right: 2.5rem; /* Adjusted to fit better with reduced height */
}

.search-button {
  border-left: none;
  border-radius: 0 9999px 9999px 0; /* Rounded right corners */
}

.search-bar input:focus,
.search-bar button:focus {
  box-shadow: 0 0 0 0 rgba(111, 164, 248, 0.5);
}

/* Other existing styles */
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
  text-decoration: none;
}

.video-title:hover {
  text-decoration: underline;
}

.video-channel {
  @apply truncate hover:text-blue-500 transition-colors duration-200;
}

.play-button {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white opacity-80 cursor-pointer;
}

.video-thumbnail:hover .play-button {
  @apply opacity-100;
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

.video-item {
  position: relative;
}

.video-thumbnail {
  position: relative;
}

.video-title {
  flex: 1;
  min-width: 0; /* 这有助于在flex容器中正确处理文本截断 */
}

.downloaded-badge {
  font-size: 0.75rem;
  line-height: 1rem;
  z-index: 10;
  display: flex;
  align-items: center;
}

/* 可以根据需要调整弹出框的样式 */
</style>
<template>
  <div class="latest-videos bg-gray-100 flex flex-col h-full">
    <div class="w-full flex-grow flex flex-col pb-4">
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

      <!-- 添加标签页 -->
      <div class="tab-container bg-white shadow-sm mb-1">
        <div class="flex justify-around">
          <button 
            v-for="tab in tabs" 
            :key="tab.value" 
            @click="activeTab = tab.value"
            :class="['px-4 py-2 text-sm font-medium', activeTab === tab.value ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500']"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div class="video-container flex-grow overflow-y-auto" ref="videoContainer" @scroll="handleScroll">
        <div
            v-for="video in videos"
            :key="video.id"
            class="video-item lg:mt-3 md:mt-3 sm:mt-3 lg:rounded-lg bg-white shadow-sm overflow-hidden relative"
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
                  @loadedmetadata="onVideoMetadataLoaded($event, video)"
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
            <!-- 修改下载标识，只在视频未播放时显示 -->
            <div v-if="video.if_downloaded && !video.isPlaying" class="downloaded-badge absolute top-2 right-2 bg-gray-200 bg-opacity-70 text-gray-700 px-2 py-0.5 rounded-full text-xs font-medium opacity-80 hover:opacity-60 transition-opacity duration-200 backdrop-filter: blur(2px);">
              已下载
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
        class="options-menu fixed bg-white shadow-lg rounded-lg py-2 z-50 w-48"
        :style="{ top: optionsPosition.top + 'px', left: optionsPosition.left + 'px' }"
        @click.stop
    >
      <button @click="toggleReadStatus(true)" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        标记为已读
      </button>
      <button @click="toggleReadStatus(false)" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        标记为未读
      </button>
      <button @click="markReadBatch('above')" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
        以上标记为已读
      </button>
      <button @click="markReadBatch('below')" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
        以下标记为已读
      </button>
      <button @click="downloadVideo" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        下载
      </button>
      <button @click="copyVideoLink" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-2.5" />
        </svg>
        复制链接
      </button>
      <button @click="dislikeVideo" class="option-item">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
        </svg>
        不喜欢
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
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
const observers = ref({});

const activeTab = ref('all');
const tabs = [
  { label: '全部', value: 'all' },
  { label: '未读', value: 'unread' },
  { label: '已读', value: 'read' },
];

const handleScroll = () => {
  if (loadTrigger.value && videoContainer.value) {
    const containerRect = videoContainer.value.getBoundingClientRect();
    const triggerRect = loadTrigger.value.getBoundingClientRect();

    if (triggerRect.top <= containerRect.bottom + 100) {
      console.log('Trigger element is visible, loading more...');
      loadMore();
    }

    const scrollTop = videoContainer.value.scrollTop;
    isScrollingUp.value = scrollTop < lastScrollTop;
    lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;

    // 在滚动时关闭选项菜单
    closeOptions();
  }
};

const loadMore = async () => {
  if (loading.value || allLoaded.value) {
    console.log('Already loading or all loaded, skipping...');
    return;
  }

  console.log('Loading more videos...');
  loading.value = true;
  try {
    const response = await axios.get('/api/channel-video/list', {
      params: {
        page: currentPage.value,
        pageSize: 10,
        query: searchQuery.value,
        read_status: activeTab.value === 'all' ? null : activeTab.value
      }
    });
    console.log('API response:', response.data);
    if (response.data.code === 0) {
      const newVideos = response.data.data.data.map(video => ({
        ...video,
        isPlaying: false,
        video_url: null
      }));
      if (newVideos.length === 0) {
        console.log('No more videos to load');
        allLoaded.value = true;
      } else {
        videos.value.push(...newVideos);
        currentPage.value++;
        console.log('New videos added, total count:', videos.value.length);
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

const dislikeVideo = async () => {
  if (activeVideo.value) {
    try {
      const response = await axios.post('/api/channel-video/dislike', {
        channel_id: activeVideo.value.channel_id,
        video_id: activeVideo.value.video_id
      });

      if (response.data.code === 0) {
        showToast('已标记为不喜欢');
        // 从列表中移除该视频
        videos.value = videos.value.filter(v => v.id !== activeVideo.value.id);
      } else {
        throw new Error(response.data.msg || '操作失败');
      }
    } catch (error) {
      console.error('标记不喜欢失败:', error);
      showToast('标记不喜欢失败: ' + (error.message || '未知错误'), true);
    }
  }
  closeOptions();
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

  // 创建并启动 Intersection Observer
  nextTick(() => {
    const videoElement = videoRefs.value[video.id];
    if (videoElement) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting && video.isPlaying) {
              videoElement.pause();
              video.isPlaying = false;
            }
          });
        },
        { threshold: 0.5 } // 当视频有一半不可见时触发
      );
      observer.observe(videoElement);
      observers.value[video.id] = observer;
    }
  });
};

const onVideoPlay = (video) => {
  video.isPlaying = true;
};

const onVideoPause = (video) => {
  // 不要在这里设置 isPlaying 为 false，让用户可以暂停后继续播放
};

const onVideoEnded = (video) => {
  video.isPlaying = false;
  // 停止观察这个视频
  if (observers.value[video.id]) {
    observers.value[video.id].disconnect();
    delete observers.value[video.id];
  }
};

const onFullscreenChange = (event) => {
  const videoElement = event.target;
  if (document.fullscreenElement) {
    // 进入全屏
    const aspectRatio = videoElement.videoWidth / videoElement.videoHeight;
    if (aspectRatio < 1) {
      // 竖屏视频
      videoElement.style.width = '100%';
      videoElement.style.height = '100%';
      videoElement.style.objectFit = 'contain';
    } else {
      // 横屏视频
      videoElement.style.width = '100%';
      videoElement.style.height = '100%';
      videoElement.style.objectFit = 'contain';
    }
  } else {
    // 退出全屏
    onVideoMetadataLoaded({ target: videoElement }, null);
  }
};

const onVideoMetadataLoaded = (event, video) => {
  const videoElement = event.target;
  const aspectRatio = videoElement.videoWidth / videoElement.videoHeight;
  
  if (aspectRatio < 1) {
    // 竖屏视频
    videoElement.style.width = '100%';
    videoElement.style.height = 'auto';
    videoElement.style.maxHeight = '100%';
  } else {
    // 横屏视频
    videoElement.style.width = '100%';
    videoElement.style.height = '100%';
    videoElement.style.objectFit = 'contain';
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
      const containerRect = videoContainer.value.getBoundingClientRect();
      
      // 计算左侧位置，确保不会超出容器右侧
      const left = Math.min(
        rect.left,
        containerRect.right - 160 // 40px 的宽度
      );
      
      optionsPosition.value = {
        top: rect.bottom + window.scrollY,
        left: Math.max(containerRect.left, left) // 确保不会超出容器左侧
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

// 修改这个函数来防止立即重新打开选项菜单
const closeOptionsOnOutsideClick = (event) => {
  if (activeOptions.value && !event.target.closest('.video-item')) {
    closeOptions();
  }
};

const toggleReadStatus = async (isRead) => {
  if (activeVideo.value) {
    try {
      await axios.post('/api/channel-video/mark-read', {
        channel_id: activeVideo.value.channel_id,
        video_id: activeVideo.value.video_id,
        is_read: isRead
      });
      activeVideo.value.if_read = isRead;
      showToast(`视频已标记为${isRead ? '已读' : '未读'}`);
    } catch (error) {
      console.error('更新阅读状态失败:', error);
      showToast('更新阅读状态失败', true);
    }
  }
  closeOptions();
};

const markReadBatch = async (direction) => {
  if (activeVideo.value) {
    try {
      await axios.post('/api/channel-video/mark-read-batch', {
        is_read: true,
        direction: direction,
        reference_id: activeVideo.value.id  // 使用 id 而不是 uploaded_at
      });
      // 更新本地视频列表的阅读状态
      videos.value.forEach(video => {
        if (direction === 'above' && video.id >= activeVideo.value.id) {
          video.if_read = true;
        } else if (direction === 'below' && video.id <= activeVideo.value.id) {
          video.if_read = true;
        }
      });
      showToast(`已将${direction === 'above' ? '以上' : '以下'}视频标记为已读`);
    } catch (error) {
      console.error('批量更新阅读状态失败:', error);
      showToast('批量更新阅读状态失败', true);
    }
  }
  closeOptions();
};

// 监听 activeTab 变化
watch(activeTab, () => {
  videos.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  error.value = null;
  loadMore();
});

onMounted(() => {
  console.log('Component mounted, loading initial videos...');
  loadMore();
  if (videoContainer.value) {
    videoContainer.value.addEventListener('scroll', handleScroll);
  }
  window.addEventListener('orientationchange', handleOrientationChange);
  document.addEventListener('click', closeOptionsOnOutsideClick);
  adjustVideoContainerHeight();
  window.addEventListener('resize', adjustVideoContainerHeight);
});

onUnmounted(() => {
  if (videoContainer.value) {
    videoContainer.value.removeEventListener('scroll', handleScroll);
  }
  window.removeEventListener('orientationchange', handleOrientationChange);
  document.removeEventListener('click', closeOptionsOnOutsideClick);
  window.removeEventListener('resize', adjustVideoContainerHeight);
  // 清理所有的 Intersection Observers
  Object.values(observers.value).forEach(observer => observer.disconnect());
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

const adjustVideoContainerHeight = () => {
  if (videoContainer.value) {
    const windowHeight = window.innerHeight;
    const searchBarHeight = document.querySelector('.search-bar')?.offsetHeight || 0;
    const newHeight = windowHeight - searchBarHeight;
    videoContainer.value.style.height = `${newHeight}px`;
    videoContainer.value.style.paddingBottom = '1rem'; // 添加一些底部内边距
  }
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
  padding: 0.5rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease-in-out;
}

.search-bar.hidden {
  transform: translateY(-100%);
}

.search-input {
  border-right: none;
  border-radius: 9999px 0 0 9999px;
}

.clear-button {
  right: 2.5rem;
}

.search-button {
  border-left: none;
  border-radius: 0 9999px 9999px 0;
}

.search-bar input:focus,
.search-bar button:focus {
  box-shadow: 0 0 0 0 rgba(111, 164, 248, 0.5);
}

.video-container {
  scrollbar-width: none;
  -ms-overflow-style: none;
  padding-bottom: 1rem; /* 添加一些底部内边距 */
}

.video-container::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.video-thumbnail {
  @apply relative pt-[56.25%] cursor-pointer;
  height: 0;
}

.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center bg-black;
}

.video-player {
  @apply max-w-full max-h-full;
  width: 100%;
  height: 100%;
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
  min-width: 0;
}

.downloaded-badge {
  font-size: 0.75rem;
  line-height: 1rem;
  z-index: 20;
  opacity: 0.8;
  transition: opacity 0.3s ease;
  backdrop-filter: blur(2px);
}

.video-thumbnail:hover .downloaded-badge {
  opacity: 0.6;
}

.options-menu {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.option-item {
  @apply flex items-center w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-150 ease-in-out;
}

.option-item:first-child {
  @apply rounded-t-lg;
}

.option-item:last-child {
  @apply rounded-b-lg;
}

.option-item:hover {
  @apply bg-blue-50 text-blue-600;
}

.option-item svg {
  @apply text-gray-400 group-hover:text-blue-500 transition-colors duration-150 ease-in-out;
}

.tab-container {
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
}
</style>
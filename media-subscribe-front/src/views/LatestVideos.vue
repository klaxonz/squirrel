<template>
  <div class="latest-videos bg-gray-100 flex flex-col h-full">
    <SearchBar @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div class="video-container flex-grow overflow-y-auto" ref="videoContainer" @scroll="handleScroll">
      <div class="video-grid sm:grid sm:grid-cols-2 sm:gap-4 p-4">
        <VideoItem
          v-for="video in videos"
          :key="video.id"
          :video="video"
          @play="playVideo"
          @setVideoRef="setVideoRef"
          @videoPlay="onVideoPlay"
          @videoPause="onVideoPause"
          @videoEnded="onVideoEnded"
          @fullscreenChange="onFullscreenChange"
          @videoMetadataLoaded="onVideoMetadataLoaded"
          @toggleOptions="toggleOptions"
          @goToChannel="goToChannelDetail"
        />
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
import { nextTick, onMounted, onUnmounted, ref, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from '../utils/axios';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import VideoItem from '../components/VideoItem.vue';
import OptionsMenu from '../components/OptionsMenu.vue';

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

const videoCounts = ref({
  all: 0,
  unread: 0,
  read: 0
});

const tabsWithCounts = computed(() => {
  return tabs.map(tab => ({
    ...tab,
    count: videoCounts.value[tab.value]
  }));
});

const isReadPage = computed(() => activeTab.value === 'read');

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
      // 更新视频计数
      videoCounts.value = response.data.data.counts;
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

const handleSearch = (query) => {
  searchQuery.value = query;
  handleSearchClick();
};

const handleSearchClick = () => {
  videos.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  error.value = null;
  loadMore();
};

const refreshList = () => {
  videos.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  error.value = null;
  loadMore();
};

const toggleReadStatus = async (isRead) => {
  if (activeVideo.value) {
    try {
      await axios.post('/api/channel-video/mark-read', {
        channel_id: activeVideo.value.channel_id,
        video_id: activeVideo.value.video_id,
        is_read: isRead
      });
      showToast(`视频已标记为${isRead ? '已读' : '未读'}`);
      refreshList(); // 刷新列表
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
        reference_id: activeVideo.value.id
      });
      showToast(`已将${direction === 'above' ? '以上' : '以下'}视频标记为已读`);
      refreshList(); // 刷新列表
    } catch (error) {
      console.error('批量更新阅读状态失败:', error);
      showToast('批量更新阅读状态失败', true);
    }
  }
  closeOptions();
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
        refreshList(); // 刷新列表
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
      
      // 计算菜单的宽度和高度（假设为 160px 宽，200px 高）
      const menuWidth = 160;
      const menuHeight = 200;
      
      // 计算左侧位置
      let left = rect.left;
      if (left + menuWidth > containerRect.right) {
        left = containerRect.right - menuWidth;
      }
      left = Math.max(containerRect.left, left);
      
      // 计算顶部位置
      let top = rect.bottom + window.scrollY;
      if (top + menuHeight > window.innerHeight) {
        top = rect.top + window.scrollY - menuHeight;
      }
      
      optionsPosition.value = { top, left };
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

const setVideoRef = (id, el) => {
  if (el) videoRefs.value[id] = el;
};
</script>

<style scoped>
.latest-videos {
  @apply min-h-full;
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

.video-grid {
  @apply grid-cols-1 sm:grid-cols-2;
}

:deep(.custom-tab-bar) {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0.2rem 0;
}

:deep(.custom-tab-bar .tab-item) {
  font-size: 0.875rem;
  padding: 0.25rem 0.5rem;
  margin: 0 0.25rem;
  border-radius: 0.25rem;
  transition: background-color 0.2s;
}

:deep(.custom-tab-bar .tab-item.active) {
  background-color: #42b983;
  color: #fff;
}

:deep(.custom-tab-bar .tab-count) {
  font-size: 0.75rem;
  background-color: #ccc;
  color: #fff;
  border-radius: 0.25rem;
  padding: 0.125rem 0.25rem;
  margin-left: 0.25rem;
}
</style>
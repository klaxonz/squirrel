<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar for desktop -->
    <Sidebar v-if="!isMobile" :routes="sidebarRoutes" />
    
    <!-- Main content area -->
    <main class="flex-1 relative">
      <div class="page-container absolute inset-0">
        <div class="content-container scrollbar-hide">
          <router-view></router-view>
        </div>
      </div>
    </main>

    <!-- Mobile navigation -->
    <MobileNav v-if="isMobile" :routes="mobileRoutes" />
  </div>
</template>

<script setup>
import { provide, ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import mitt from 'mitt';
import VideoModal from './components/VideoModal.vue';
import MobileNav from './components/MobileNav.vue';
import Sidebar from './components/Sidebar.vue';
import { HomeIcon, BookmarkIcon, CogIcon, ArrowDownTrayIcon, ClockIcon, SpeakerWaveIcon } from '@heroicons/vue/24/outline';
import useVideoOperations from './composables/useVideoOperations';
import useToast from './composables/useToast';
import AudioPlayer from './components/AudioPlayer.vue';
import axios from 'axios';
import { useWindowSize } from '@vueuse/core'
import './styles/layout.css'

const router = useRouter();
const emitter = mitt();
provide('emitter', emitter);

const { width } = useWindowSize()
const isMobile = computed(() => width.value < 768)

// 添加视频播放相关的状态
const isModalOpen = ref(false);
const selectedVideo = ref(null);
const currentPlaylist = ref([]);
const videos = ref([]);

// 使用视频操作 composable
const {
  playVideo,
  changeVideo,
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
} = useVideoOperations(videos);

const { toastMessage, showToast, displayToast } = useToast();

const routes = ref([
  { path: '/', name: '首页', icon: HomeIcon },
  { path: '/subscribed', name: '订阅', icon: BookmarkIcon },
  { path: '/podcasts', name: '播客', icon: SpeakerWaveIcon },
  { path: '/history', name: '历史记录', icon: ClockIcon },
  { path: '/downloads', name: '下载任务', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);

const isCollapsed = ref(false);

const handleSidebarCollapse = (collapsed) => {
  isCollapsed.value = collapsed;
  emitter.emit('sidebarStateChanged');
};

// 添加视频模态框相关方法
const openVideoModal = async (video, playlist) => {
  emitter.emit('closeMiniPlayer');
  selectedVideo.value = video;
  currentPlaylist.value = playlist;
  isModalOpen.value = true;
  await playVideo(video);
};

const closeVideoModal = () => {
  isModalOpen.value = false;
  selectedVideo.value = null;
};

const handleChangeVideo = async (newVideo) => {
  try {
    const updatedVideo = await changeVideo(newVideo);
    if (updatedVideo) {
      selectedVideo.value = updatedVideo;
    }
  } catch (err) {
    console.error('切换视频失败:', err);
    displayToast('切换视频失败');
  }
};

const handleGoToChannel = (channelId) => {
  router.push(`/channel/${channelId}/all`);
};

// 监听视频模态框打开事件
onMounted(() => {
  emitter.on('openVideoModal', ({ video, playlist }) => {
    openVideoModal(video, playlist);
  });
});

onUnmounted(() => {
  emitter.all.clear();
});

// 添加播客相关状态
const currentEpisode = ref(null);
const currentPodcast = ref(null);

// 提供全局方法来控制播放器
provide('playPodcast', (episode, podcast) => {
  currentEpisode.value = episode;
  currentPodcast.value = podcast;
});

// 播放器控制方法
const updateProgress = async (position) => {
  if (!currentEpisode.value) return;
  // try {
  //   await axios.post(`/api/podcasts/episodes/${currentEpisode.value.id}/progress`, {
  //     position: Math.floor(position)
  //   });
  // } catch (error) {
  //   console.error('Failed to update progress:', error);
  // }
};

const onEpisodeEnded = async () => {
  if (!currentEpisode.value) return;
  try {
    await axios.post(`/api/podcasts/episodes/${currentEpisode.value.id}/mark-read`, {
      is_read: true
    });
  } catch (error) {
    console.error('Failed to mark episode as read:', error);
  }
  currentEpisode.value = null;
  currentPodcast.value = null;
};

const closeAudioPlayer = () => {
  currentEpisode.value = null;
  currentPodcast.value = null;
};

const sidebarRoutes = computed(() => {
  return routes.value.filter(route => !route.path.includes('/settings'))
})

const mobileRoutes = computed(() => {
  return routes.value
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

:root {
  --font-sans: 'Roboto', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
}

html, body {
  @apply h-full overflow-hidden;
  overscroll-behavior: none;
}

body {
  font-family: var(--font-sans);
  @apply bg-[#0f0f0f] text-white;
}

.app-container {
  font-family: var(--font-sans);
}

.nav-item {
  @apply flex items-center px-4 py-2 text-[#f1f1f1] hover:bg-[#272727] rounded-lg mx-2 transition-all duration-200 ease-in-out overflow-hidden;
  white-space: nowrap;
}

.nav-item.active {
  @apply bg-[#272727] text-white;
}

.nav-item .w-6 {
  @apply text-[#f1f1f1] transition-all duration-300 ease-in-out flex-shrink-0;
}

.nav-item:hover .w-6,
.nav-item.active .w-6 {
  @apply text-white;
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-sans);
}

button {
  @apply focus:outline-none;
}

/* 添加一些全局样式来增强整体视觉效果 */
.hover-lift {
  @apply transition-transform duration-300 ease-in-out hover:-translate-y-1;
}

/* 添加文字过渡效果 */
.nav-item span {
  display: inline-block;
  transition: opacity 0.3s ease-in-out, width 0.3s ease-in-out;
}
</style>

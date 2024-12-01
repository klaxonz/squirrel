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

    <!-- Video Modal -->
    <Teleport to="body">
      <VideoModal
        v-if="isModalOpen"
        :isOpen="isModalOpen"
        :video="selectedVideo"
        :playlist="currentPlaylist"
        @close="closeVideoModal"
        @videoPlay="onVideoPlay"
        @videoPause="onVideoPause"
        @videoEnded="onVideoEnded"
        @changeVideo="handleChangeVideo"
        @goToChannel="handleGoToChannel"
      />
    </Teleport>

    <!-- 全局播放器 -->
    <Teleport to="body">
      <PodcastPlayer
        v-if="currentPodcast && currentEpisode"
        :podcast="currentPodcast"
        :currentEpisode="currentEpisode"
        :isPlaying="isPlaying"
        @play="handlePodcastPlay"
        @pause="handlePodcastPause"
        @timeupdate="handlePodcastTimeUpdate"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { provide, ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import mitt from 'mitt';
import VideoModal from './components/VideoModal.vue';
import MobileNav from './components/MobileNav.vue';
import Sidebar from './components/Sidebar.vue';
import PodcastPlayer from './components/PodcastPlayer.vue';
import { HomeIcon, BookmarkIcon, CogIcon, ArrowDownTrayIcon, ClockIcon, SpeakerWaveIcon } from '@heroicons/vue/24/outline';
import useVideoOperations from './composables/useVideoOperations';
import useToast from './composables/useToast';
import { useWindowSize } from '@vueuse/core'
import './styles/layout.css'
import { usePodcasts } from './composables/usePodcasts';

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

const {displayToast } = useToast();

const routes = ref([
  { path: '/', name: '首页', icon: HomeIcon },
  { path: '/subscribed', name: '订阅', icon: BookmarkIcon },
  { path: '/podcasts', name: '播客', icon: SpeakerWaveIcon },
  { path: '/history', name: '历史记录', icon: ClockIcon },
  { path: '/downloads', name: '下载任务', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);

// 添加视频模态框相关方法
const openVideoModal = async (video, playlist) => {
  console.log('Opening video modal with:', video);
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
  console.log('Setting up video modal event listener');
  emitter.on('openVideoModal', ({ video, playlist }) => {
    console.log('Received openVideoModal event:', video);
    openVideoModal(video, playlist);
  });
});

onUnmounted(() => {
  emitter.all.clear();
});

// 添加播客相关状态
const currentEpisode = ref(null);
const currentPodcast = ref(null);
const isPlaying = ref(false);

// 提供全局状态
provide('currentPodcast', currentPodcast);
provide('currentEpisode', currentEpisode);
provide('isPlaying', isPlaying);

// 提供全局方法来控制播放器
provide('playPodcast', (episode, podcast) => {
  currentEpisode.value = episode;
  currentPodcast.value = podcast;
  isPlaying.value = true;
});

// 播放器控制方法
const handlePodcastPlay = () => {
  isPlaying.value = true;
};

const handlePodcastPause = () => {
  isPlaying.value = false;
};

const { updatePlayProgress } = usePodcasts();

const handlePodcastTimeUpdate = ({ position, duration }) => {
  if (currentEpisode.value) {
    updatePlayProgress(currentEpisode.value.id, position, duration);
  }
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

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-sans);
}

button {
  @apply focus:outline-none;
}

</style>

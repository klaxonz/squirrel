<template>
  <div class="app-container flex h-screen bg-[#0f0f0f] text-white">
    <!-- 侧边栏 -->
    <nav :class="['sidebar h-full overflow-y-auto flex-shrink-0 transition-all duration-300 ease-in-out bg-[#0f0f0f]', 
                  isCollapsed ? 'w-20' : 'w-48']">
      <div class="flex flex-col h-full">
        <div class="logo p-4 flex items-center mx-2">
          <button @click="toggleSidebar" class="mr-4 text-white hover:text-gray-300 focus:outline-none">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
        <ul class="flex-grow py-2">
          <li v-for="route in routes" :key="route.path">
            <router-link :to="route.path" class="nav-item" :class="{ active: $route.path === route.path }" :title="isCollapsed ? route.name : ''">
              <component :is="route.icon" class="w-6 h-6" :class="{'mr-4': !isCollapsed}" />
              <span :class="['text-sm transition-all duration-300 ease-in-out', 
                           isCollapsed ? 'opacity-0 w-0' : 'opacity-100 w-auto']">
                {{ route.name }}
              </span>
            </router-link>
          </li>
        </ul>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="flex-grow overflow-hidden bg-[#0f0f0f]">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>

    <!-- 添加 VideoModal -->
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

    <Teleport to="body">
      <div v-if="showToast" class="toast-message">
        {{ toastMessage }}
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { provide, ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import mitt from 'mitt';
import VideoModal from './components/VideoModal.vue';
import MiniPlayer from './components/MiniPlayer.vue';
import { HomeIcon, BookmarkIcon, CogIcon, ArrowDownTrayIcon, ClockIcon } from '@heroicons/vue/24/outline';
import useVideoOperations from './composables/useVideoOperations';
import useToast from './composables/useToast';

const router = useRouter();
const emitter = mitt();
provide('emitter', emitter);

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
  { path: '/subscriptions', name: '订阅', icon: BookmarkIcon },
  { path: '/history', name: '历史记录', icon: ClockIcon },
  { path: '/download-tasks', name: '下载任务', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);

const isCollapsed = ref(false);

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
  // 触发侧边栏状态改变事件
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
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

:root {
  --font-sans: 'Roboto', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
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

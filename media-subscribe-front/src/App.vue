<template>
  <div class="app-container flex h-screen bg-[#0f0f0f] text-white">
    <!-- 侧边栏 -->
    <nav :class="['sidebar h-full overflow-y-auto flex-shrink-0 transition-all duration-300 ease-in-out bg-[#0f0f0f]', 
                  isCollapsed ? 'w-20' : 'w-64']">
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
              <span v-if="!isCollapsed" class="text-sm">{{ route.name }}</span>
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

    <!-- 添加迷你播放器 -->
    <MiniPlayer
      v-if="miniPlayerVideo"
      :video="miniPlayerVideo"
      :isCollapsed="isCollapsed"
      :currentTime="savedTime"
      @close="closeMiniPlayer"
      @expandToModal="expandToModal"
      @timeUpdate="updateSavedTime"
    />
  </div>
</template>

<script setup>
import { provide, ref, onUnmounted } from 'vue';
import mitt from 'mitt';
import MiniPlayer from './components/MiniPlayer.vue';
import { HomeIcon, FireIcon, ClockIcon, BookmarkIcon, FilmIcon, CogIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline';

const emitter = mitt();
provide('emitter', emitter);

const routes = ref([
  { path: '/', name: '首页', icon: HomeIcon },
  // { path: '/trending', name: '趋势', icon: FireIcon },
  { path: '/subscriptions', name: '订阅', icon: BookmarkIcon },
  // { path: '/library', name: '媒体库', icon: FilmIcon },
  // { path: '/history', name: '历史记录', icon: ClockIcon },
  { path: '/download-tasks', name: '下载任务', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);

const isCollapsed = ref(false);

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
};

const miniPlayerVideo = ref(null);
const savedTime = ref(0);

// 监听最小化播放器事件
emitter.on('minimizePlayer', (data) => {
  miniPlayerVideo.value = data.video;
  savedTime.value = data.currentTime || 0;
});

const closeMiniPlayer = () => {
  miniPlayerVideo.value = null;
  savedTime.value = 0;
};

const expandToModal = (video) => {
  emitter.emit('openVideoModal', { 
    video: {
      ...video,
      video_url: video.video_url,
      audio_url: video.audio_url
    }, 
    currentTime: video.currentTime || savedTime.value 
  });
  closeMiniPlayer();
};

const updateSavedTime = (time) => {
  savedTime.value = time;
};

// 监听关闭迷你播放器事件
emitter.on('closeMiniPlayer', () => {
  closeMiniPlayer();
});

// 确保 emitter 在组件卸载时清理事件监听
onUnmounted(() => {
  emitter.off('minimizePlayer');
  emitter.off('closeMiniPlayer');
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
  @apply flex items-center px-4 py-2 text-[#f1f1f1] hover:bg-[#272727] rounded-lg mx-2 transition-all duration-200 ease-in-out;
}

.nav-item.active {
  @apply bg-[#272727] text-white;
}

.nav-item .w-6 {
  @apply text-[#f1f1f1];
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
</style>

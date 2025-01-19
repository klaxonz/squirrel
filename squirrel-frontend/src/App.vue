<template>
  <div v-if="isAuthPage" class="h-screen overflow-hidden">
    <router-view />
  </div>
  <div v-else class="flex h-screen overflow-hidden">
    <!-- Sidebar for desktop -->
    <Sidebar v-if="!isMobile" :routes="sidebarRoutes" />
    
    <!-- Main content area -->
    <main class="flex-1 relative">
      <div class="page-container absolute inset-0">
        <div class="content-container scrollbar-hide">
          <router-view v-slot="{ Component }">
            <keep-alive :include="['LatestVideos']">
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </div>
    </main>

    <!-- Mobile navigation -->
    <MobileNav v-if="isMobile" :routes="mobileRoutes" />

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
import mitt from 'mitt';
import MobileNav from './components/MobileNav.vue';
import Sidebar from './components/Sidebar.vue';
import PodcastPlayer from './components/PodcastPlayer.vue';
import { HomeIcon, BookmarkIcon, CogIcon, ArrowDownTrayIcon, ClockIcon, SpeakerWaveIcon } from '@heroicons/vue/24/outline';
import { useWindowSize } from '@vueuse/core'
import { useRoute } from 'vue-router';
import './styles/layout.css'
import { usePodcasts } from './composables/usePodcasts';
import { useUser } from './composables/useUser';

const route = useRoute();
const emitter = mitt();
provide('emitter', emitter);

const { width } = useWindowSize()
const isMobile = computed(() => width.value < 768)

// 判断是否是认证页面(登录/注册)
const isAuthPage = computed(() => {
  return ['/login', '/register'].includes(route.path);
});

const routes = ref([
  { path: '/', name: '首页', icon: HomeIcon },
  { path: '/subscribed', name: '订阅', icon: BookmarkIcon },
  { path: '/podcasts', name: '播客', icon: SpeakerWaveIcon },
  { path: '/history', name: '历史记录', icon: ClockIcon },
  { path: '/downloads', name: '下载任务', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);


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

const { getCurrentUser } = useUser();

onMounted(async () => {
  if (localStorage.getItem('token')) {
    try {
      await getCurrentUser();
    } catch (error) {
      console.error('Failed to get user info:', error);
    }
  }
});

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

<template>
  <div class="app-container flex h-screen bg-gray-100">
    <!-- 侧边栏 -->
    <nav class="sidebar w-56 bg-white h-full overflow-y-auto flex-shrink-0 border-r border-gray-200">
      <div class="logo h-16 px-6 flex items-center">
        <img src="/squirrel-icon.svg" alt="Squirrel" class="w-8 h-8 mr-2" />
        <h1 class="text-xl font-semibold text-gray-900">Squirrel</h1>
      </div>
      <ul class="mt-2">
        <li v-for="route in routes" :key="route.path">
          <router-link :to="route.path" class="nav-item" :class="{ active: $route.path === route.path }">
            <component :is="route.icon" class="w-6 h-6 mr-4" />
            {{ route.name }}
          </router-link>
        </li>
      </ul>
    </nav>

    <!-- 主内容区 -->
    <main class="flex-grow overflow-hidden bg-white">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { provide, ref } from 'vue';
import mitt from 'mitt';
import { HomeIcon, BookmarkIcon, CogIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline';

const emitter = mitt();
provide('emitter', emitter);

const routes = ref([
  { path: '/', name: '首页', icon: HomeIcon },
  { path: '/subscribed', name: '订阅', icon: BookmarkIcon },
  { path: '/download-tasks', name: '下载', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);
</script>

<style scoped>
.app-container {
  font-family: 'Roboto', 'Arial', sans-serif;
}

.nav-item {
  @apply flex items-center px-6 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-150 ease-in-out;
}

.nav-item.active {
  @apply bg-gray-100 font-medium text-red-600;
}
</style>
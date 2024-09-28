<template>
  <div class="app-container bg-gray-50 flex h-screen">
    <!-- 侧边栏 -->
    <nav class="sidebar w-60 bg-white border-r border-gray-200 p-4">
      <div class="logo mb-8">
        <h1 class="text-xl font-semibold text-gray-800">Squirrel</h1>
      </div>
      <ul class="space-y-1">
        <li v-for="route in routes" :key="route.path">
          <router-link :to="route.path" class="nav-item" :class="{ active: $route.path === route.path }">
            <component :is="route.icon" class="w-4 h-4 mr-3" />
            {{ route.name }}
          </router-link>
        </li>
      </ul>
    </nav>

    <!-- 主内容区 -->
    <main class="flex-grow overflow-hidden">
      <div class="h-full overflow-y-auto px-8 py-6">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import {provide, ref} from 'vue';
import mitt from 'mitt';
import { HomeIcon, BookmarkIcon, CogIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline';

const emitter = mitt();
provide('emitter', emitter);

const routes = ref([
  { path: '/', name: '最新', icon: HomeIcon },
  { path: '/subscribed', name: '订阅', icon: BookmarkIcon },
  { path: '/download-tasks', name: '下载', icon: ArrowDownTrayIcon },
  { path: '/settings', name: '设置', icon: CogIcon },
]);
</script>

<style scoped>
.app-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.nav-item {
  @apply flex items-center px-3 py-2 text-sm text-gray-600 rounded-lg transition-colors duration-150 ease-in-out;
}

.nav-item:hover {
  @apply bg-gray-100 text-gray-900;
}

.nav-item.active {
  @apply bg-blue-50 text-blue-600;
}
</style>
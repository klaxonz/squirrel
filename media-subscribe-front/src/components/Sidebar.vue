<template>
  <div class="sidebar bg-[#0f0f0f] h-full flex flex-col"
       :class="[isCollapsed ? 'w-[64px]' : 'w-[220px]']">
    <!-- 顶部菜单按钮 -->
    <div class="flex items-center h-14 px-3">
      <button
        @click="toggleCollapse"
        class="p-2 hover:bg-[#272727] rounded-full"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 overflow-y-auto py-1 scrollbar-hide">
      <!-- 主要菜单项 -->
      <div class="px-2">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center h-10 px-3 text-[#f1f1f1] rounded-lg transition-colors duration-150 mb-1"
          :class="[
            { 'justify-center': isCollapsed },
            $route.path === item.path 
              ? 'bg-[#272727]' 
              : 'hover:bg-[#ffffff1a]'
          ]"
        >
          <component
            :is="item.icon"
            class="w-5 h-5"
            :class="[isCollapsed ? '' : 'mr-4']"
          />
          <span v-if="!isCollapsed" class="text-[13px]">{{ item.name }}</span>
        </router-link>
      </div>

      <!-- 分割线 -->
      <div class="my-2 border-t border-[#ffffff1a] mx-2"></div>

      <!-- 底部菜单项 -->
      <div class="px-2">
        <router-link
          v-for="item in bottomItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center h-10 px-3 text-[#f1f1f1] rounded-lg transition-colors duration-150 mb-1"
          :class="[
            { 'justify-center': isCollapsed },
            $route.path === item.path 
              ? 'bg-[#272727]' 
              : 'hover:bg-[#ffffff1a]'
          ]"
        >
          <component
            :is="item.icon"
            class="w-5 h-5"
            :class="[isCollapsed ? '' : 'mr-4']"
          />
          <span v-if="!isCollapsed" class="text-[13px]">{{ item.name }}</span>
        </router-link>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import {
  HomeIcon,
  BookmarkIcon,
  SpeakerWaveIcon,
  ClockIcon,
  ArrowDownTrayIcon,
  Cog6ToothIcon as CogIcon
} from '@heroicons/vue/24/outline';

const route = useRoute();
const isCollapsed = ref(false);
const emit = defineEmits(['collapse']);

const menuItems = [
  {
    name: '首页',
    path: '/',
    icon: HomeIcon,
  },
  {
    name: '订阅',
    path: '/subscribed',
    icon: BookmarkIcon,
  },
  {
    name: '播客',
    path: '/podcasts',
    icon: SpeakerWaveIcon,
  },
  {
    name: '下载',
    path: '/downloads',
    icon: ArrowDownTrayIcon,
  },
  {
    name: '历史记录',
    path: '/history',
    icon: ClockIcon,
  }
];

const bottomItems = [
  {
    name: '设置',
    path: '/settings',
    icon: CogIcon,
  }
];

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value;
  emit('collapse', isCollapsed.value);
};

// 监听路由变化，在移动端自动收起侧边栏
watch(route, () => {
  if (window.innerWidth <= 768) {
    isCollapsed.value = true;
    emit('collapse', true);
  }
});
</script>

<style scoped>
.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

/* 添加平滑过渡效果 */
.sidebar {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 确保图标垂直居中 */
.router-link-active svg {
  @apply text-white;
}
</style> 
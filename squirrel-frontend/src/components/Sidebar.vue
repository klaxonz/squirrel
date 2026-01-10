<template>
  <div class="sidebar bg-[#0f0f0f] h-full flex flex-col"
       :class="[isCollapsed ? 'w-[64px]' : 'w-[220px]']">
    <!-- 顶部菜单按钮 -->
    <div class="flex items-center h-14 px-3">
      <button
        @click="toggleCollapse"
        class="p-2 hover:bg-[#272727] rounded-full"
      >
        <Bars3Icon class="h-6 w-6 text-white" />
      </button>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 overflow-y-auto py-1 scrollbar-hide">
      <!-- 主要菜单项 -->
      <div class="px-2">
        <SidebarMenuItem
          v-for="item in MENU_ITEMS.main"
          :key="item.path"
          :item="item"
          :is-collapsed="isCollapsed"
          :is-active="$route.path === item.path"
        />
      </div>

      <!-- 分割线 -->
      <div class="my-2 border-t border-[#ffffff1a] mx-2"></div>

      <!-- 底部菜单项 -->
      <div class="px-2">
        <SidebarMenuItem
          v-for="item in MENU_ITEMS.bottom"
          :key="item.path"
          :item="item"
          :is-collapsed="isCollapsed"
          :is-active="$route.path === item.path"
        />
      </div>
    </nav>

    <!-- 底部退出按钮 -->
    <div class="px-2 py-1 border-t border-[#ffffff1a]">
      <button
        @click="handleLogout"
        class="flex items-center h-10 px-3 text-[#f1f1f1] rounded-lg transition-colors duration-150 w-full"
        :class="[
          { 'justify-center': isCollapsed },
          'hover:bg-[#ffffff1a]'
        ]"
      >
        <ArrowRightOnRectangleIcon class="w-5 h-5" :class="[isCollapsed ? '' : 'mr-4']" />
        <span v-if="!isCollapsed" class="text-[13px]">退出登录</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bars3Icon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/vue/24/outline'
import { useUser } from '../composables/useUser'
import SidebarMenuItem from './SidebarMenuItem.vue'
import { MENU_ITEMS } from '../constants/sidebar'

const route = useRoute()
const router = useRouter()
const isCollapsed = ref(false)
const emit = defineEmits(['collapse'])
const emitter = inject('emitter')
const { logout } = useUser()

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value;
  emit('collapse', isCollapsed.value);
  emitter.emit('sidebarStateChanged');
};

const handleLogout = () => {
  logout();
  router.push('/login');
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

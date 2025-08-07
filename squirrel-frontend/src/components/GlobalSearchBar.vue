<template>
  <div class="global-search-bar bg-[#0f0f0f] border-[#272727] px-4 py-3">
    <div class="max-w-2xl mx-auto">
      <div class="relative flex items-center w-full">
        <input
          v-model="searchQuery"
          @keyup.enter="handleSearch"
          @keyup.esc="clearSearch"
          @input="handleInput"
          type="text"
          :placeholder="currentPlaceholder"
          class="w-full h-10 pl-10 pr-12 text-sm bg-[#222222] border border-[#303030] rounded-full focus:outline-none focus:border-[#4a4a4c] text-white placeholder-gray-400"
        >
        <button
          @click="handleSearch"
          class="absolute left-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
          </svg>
        </button>
        
        <!-- 清除按钮 -->
        <button
          v-if="searchQuery"
          @click="clearSearch"
          title="清除搜索 (ESC)"
          class="absolute right-3 top-1/2 transform -translate-y-1/2 focus:outline-none hover:text-white hover:bg-white/10 text-gray-400 rounded-full p-1 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const emitter = inject('emitter');

// 为每个页面单独保存搜索状态
const searchStates = ref({
  'Subscribed': '',
  'LatestVideos': '',
  'AllVideos': '',
  'UnreadVideos': '',
  'ReadVideos': '',
  'PreviewVideos': '',
  'LikedVideos': '',
  'SubscriptionDetail': '',
  'SubscriptionAllVideos': '',
  'Podcasts': '',
  'History': '',
  'Downloads': ''
});

const searchQuery = ref('');

// 根据当前路由确定占位符文本
const currentPlaceholder = computed(() => {
  const routeName = route.name;

  switch (routeName) {
    case 'Subscribed':
      return '搜索频道...';
    case 'LatestVideos':
    case 'AllVideos':
    case 'UnreadVideos':
    case 'ReadVideos':
    case 'PreviewVideos':
    case 'LikedVideos':
    case 'SubscriptionDetail':
    case 'SubscriptionAllVideos':
      return '搜索视频...';
    case 'Podcasts':
      return '搜索播客...';
    case 'History':
      return '搜索历史记录...';
    case 'Downloads':
      return '搜索下载任务...';
    default:
      return '搜索...';
  }
});

// 根据当前路由确定搜索事件名称
const getSearchEventName = () => {
  const routeName = route.name;

  switch (routeName) {
    case 'Subscribed':
      return 'search:subscribed';
    case 'LatestVideos':
    case 'AllVideos':
    case 'UnreadVideos':
    case 'ReadVideos':
    case 'PreviewVideos':
    case 'LikedVideos':
    case 'SubscriptionDetail':
    case 'SubscriptionAllVideos':
      return 'search:home';
    case 'Podcasts':
      return 'search:podcasts';
    case 'History':
      return 'search:history';
    case 'Downloads':
      return 'search:downloads';
    default:
      return 'search:global';
  }
};

// 处理搜索
const handleSearch = () => {
  const eventName = getSearchEventName();
  emitter.emit(eventName, searchQuery.value);
};

// 处理输入变化（防抖搜索）
let searchTimeout = null;
const handleInput = () => {
  // 清除之前的定时器
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }

  // 设置新的定时器，300ms 后触发搜索
  searchTimeout = setTimeout(() => {
    handleSearch();
  }, 300);
};

// 清除搜索
const clearSearch = () => {
  searchQuery.value = '';
  // 立即触发搜索以显示全部结果
  handleSearch();

  // 可选：给用户一个视觉反馈
  const input = document.querySelector('.global-search-bar input');
  if (input) {
    input.focus();
  }
};

// 监听路由变化，恢复对应页面的搜索状态
watch(route, (newRoute) => {
  // 保存当前页面的搜索状态
  const currentRouteName = newRoute.name;
  if (currentRouteName && searchStates.value.hasOwnProperty(currentRouteName)) {
    searchQuery.value = searchStates.value[currentRouteName];
  } else {
    searchQuery.value = '';
  }
}, { immediate: true });

// 监听搜索内容变化，保存到对应页面状态
watch(searchQuery, (newQuery) => {
  const currentRouteName = route.name;
  if (currentRouteName && searchStates.value.hasOwnProperty(currentRouteName)) {
    searchStates.value[currentRouteName] = newQuery;
  }
});

// 监听来自页面的搜索查询更新
const handleSearchQueryUpdate = (query) => {
  searchQuery.value = query;
};

onMounted(() => {
  // 监听来自页面的搜索查询更新事件
  emitter.on('updateSearchQuery', handleSearchQueryUpdate);
});

onUnmounted(() => {
  emitter.off('updateSearchQuery', handleSearchQueryUpdate);
});

// 暴露方法给父组件
defineExpose({
  focus: () => {
    const input = document.querySelector('.global-search-bar input');
    if (input) input.focus();
  },
  clear: clearSearch,
  setQuery: (query) => {
    searchQuery.value = query;
  }
});
</script>

<style scoped>
.global-search-bar {
  /* 确保搜索框在最顶层 */
  z-index: 10;
}

/* 添加平滑过渡效果 */
input {
  transition: border-color 0.2s ease-in-out;
}

input:focus {
  box-shadow: 0 0 0 2px rgba(74, 74, 76, 0.3);
}
</style>

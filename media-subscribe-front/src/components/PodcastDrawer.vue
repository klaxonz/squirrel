<template>
  <div 
    v-if="isOpen"
    class="fixed inset-0 z-50 flex"
  >
    <!-- 遮罩层 -->
    <div 
      class="absolute inset-0 bg-black/50"
      @click="handleClose"
    ></div>

    <!-- 抽屉内容 -->
    <div 
      class="relative ml-auto w-[600px] bg-[#1f1f1f] h-full flex flex-col"
    >
      <!-- 头部 -->
      <div class="relative flex-none">
        <!-- 背景图 -->
        <div class="absolute inset-0 bg-gradient-to-b from-[#272727] to-[#0f0f0f]">
          <img 
            :src="podcast.cover_url" 
            class="w-full h-full object-cover opacity-30 blur-xl"
          >
        </div>

        <!-- 内容 -->
        <div class="relative p-8">
          <div class="flex items-start space-x-8">
            <img 
              :src="podcast.cover_url" 
              :alt="podcast.title"
              class="w-48 h-48 rounded-lg shadow-2xl object-cover"
            >
            <div class="flex-grow">
              <h1 class="text-4xl font-bold">{{ podcast.title }}</h1>
              <p class="text-lg text-[#aaaaaa] mt-2">{{ podcast.author }}</p>
              <p class="text-sm text-[#aaaaaa] mt-4 line-clamp-3">{{ podcast.description }}</p>
              <div class="flex items-center mt-6 space-x-6">
                <span class="text-sm">{{ podcast.total_count }} 集</span>
                <span class="text-sm">{{ formatLastUpdate(podcast.last_updated) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 关闭按钮 -->
        <button 
          @click="handleClose"
          class="absolute top-4 right-4 p-2 text-white/50 hover:text-white rounded-full hover:bg-white/10"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 剧集列表标题 -->
      <div class="flex-none px-6 py-4 border-b border-[#272727]">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold">所有剧集</h2>
          <div class="flex items-center space-x-4">
            <button 
              v-for="sort in ['最新', '最早']" 
              :key="sort"
              @click="sortOrder = sort"
              class="text-sm transition-colors"
              :class="sortOrder === sort ? 'text-white' : 'text-[#aaaaaa] hover:text-white'"
            >
              {{ sort }}
            </button>
          </div>
        </div>
      </div>

      <!-- 剧集列表 -->
      <div class="flex-1 overflow-y-auto scrollbar-hide" @scroll="handleScroll">
        <div class="p-6">
          <!-- 剧集列表 -->
          <div class="space-y-2">
            <div 
              v-for="episode in sortedEpisodes" 
              :key="episode.id"
              class="group flex items-center p-4 rounded-lg hover:bg-[#272727] cursor-pointer transition-colors"
            >
              <div class="w-12 h-12 flex-shrink-0">
                <img 
                  :src="podcast.cover_url" 
                  class="w-full h-full rounded object-cover"
                >
              </div>
              <div class="flex-grow min-w-0 ml-4">
                <h3 class="text-sm font-medium truncate">{{ episode.title }}</h3>
                <p class="text-xs text-[#aaaaaa] mt-1 line-clamp-2">{{ episode.description }}</p>
                <div class="flex items-center mt-2 space-x-4">
                  <span class="text-xs text-[#aaaaaa]">{{ formatDate(episode.published_at) }}</span>
                  <span class="text-xs text-[#aaaaaa]">{{ formatDuration(episode.duration) }}</span>
                </div>
              </div>
              <button 
                class="p-2 text-white opacity-0 group-hover:opacity-100"
                @click="handlePlay(episode)"
              >
                <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M4 4l12 6-12 6V4z"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- 加载状态 -->
          <div v-if="loading" class="flex justify-center py-8">
            <div class="flex space-x-2">
              <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce"></div>
              <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
              <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
            </div>
          </div>
          
          <!-- 加载完成提示 -->
          <div v-if="!loading && !hasMore" class="text-center py-8 text-[#aaaaaa]">
            没有更多剧集了
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import axios from '../utils/axios';
import { formatDate, formatDuration, formatLastUpdate } from '../utils/dateFormat';

const props = defineProps({
  podcast: {
    type: Object,
    required: true
  },
  isOpen: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close', 'play']);

const sortOrder = ref('最新');
const episodes = ref(props.podcast.episodes || []);
const page = ref(1);
const loading = ref(false);
const hasMore = ref(true);
const isDestroyed = ref(false);

// 防抖函数
const debounce = (fn, delay = 300) => {
  let timer = null;
  return (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
};

// 处理关闭
const handleClose = () => {
  if (!isDestroyed.value) {
    emit('close');
  }
};

// 处理播放
const handlePlay = (episode) => {
  if (!isDestroyed.value) {
    emit('play', episode);
  }
};

// 加载剧集
const loadEpisodes = async (isLoadMore = false) => {
  if (isDestroyed.value) return;
  if (loading.value) return;
  if (isLoadMore && !hasMore.value) return;  // 如果是加载更多且没有更多数据，直接返回
  
  loading.value = true;
  try {
    const response = await axios.get(`/api/podcasts/channels/${props.podcast.id}/episodes`, {
      params: {
        page: page.value,
        page_size: 20,
        sort_order: sortOrder.value === '最新' ? 'desc' : 'asc'
      }
    });
    
    if (isDestroyed.value) return;
    
    const { items, has_more } = response.data;
    
    if (isLoadMore) {
      episodes.value = [...(episodes.value || []), ...(items || [])];
    } else {
      episodes.value = items || [];
    }
    
    hasMore.value = has_more || false;
    page.value++;
  } catch (error) {
    console.error('Failed to load episodes:', error);
    episodes.value = [];
    hasMore.value = false;
  } finally {
    if (!isDestroyed.value) {
      loading.value = false;
    }
  }
};

// 监听滚动的实际处理函数
const handleScrollImpl = (event) => {
  if (isDestroyed.value) return;
  if (!hasMore.value) return;  // 如果没有更多数据，直接返回
  
  const { scrollTop, clientHeight, scrollHeight } = event.target;
  if (scrollHeight - scrollTop <= clientHeight + 100) {
    loadEpisodes(true);
  }
};

// 使用防抖包装滚动处理函数
const handleScroll = debounce(handleScrollImpl, 200);

const sortedEpisodes = computed(() => episodes.value || []);

// 监听排序变化，重置并重新加载
watch(sortOrder, () => {
  if (isDestroyed.value) return;
  page.value = 1;
  episodes.value = [];  // 清空现有数据
  hasMore.value = true;
  loadEpisodes();
});

// 监听 isOpen 变化，重置状态
watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    page.value = 1;
    hasMore.value = true;
    episodes.value = [];
    loadEpisodes();
  }
});

// 初始加载
onMounted(() => {
  episodes.value = [];
  loadEpisodes();
});

// 组件卸载时清理
onUnmounted(() => {
  isDestroyed.value = true;
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

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style> 
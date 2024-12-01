<template>
  <div class="podcasts-page flex h-full bg-[#0f0f0f] text-white">
    <!-- 左侧导航栏 -->
    <div class="w-60 flex-shrink-0 flex flex-col border-r border-[#272727]">
      <!-- Logo/标题 -->
      <div class="p-4 border-b border-[#272727]">
        <h1 class="text-xl font-bold">播客</h1>
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 overflow-y-auto scrollbar-hide">
        <div class="p-4">
          <button
            v-for="item in navItems"
            :key="item.id"
            @click="currentView = item.id"
            class="w-full px-4 py-2 mb-1 flex items-center rounded-lg text-sm transition-colors"
            :class="currentView === item.id ? 'bg-[#272727] text-white' : 'text-[#aaaaaa] hover:text-white'"
          >
            <component :is="item.icon" class="w-5 h-5 mr-3"/>
            {{ item.label }}
          </button>
        </div>

        <!-- 分类列表 -->
        <div class="px-4 mt-2">
          <h3 class="px-4 text-xs font-medium text-[#aaaaaa] uppercase mb-2">分类</h3>
          <button
            v-for="category in categories"
            :key="category.value"
            @click="activeCategory = category.value"
            class="w-full px-4 py-2 mb-1 text-left rounded-lg text-sm transition-colors"
            :class="activeCategory === category.value ? 'bg-[#272727] text-white' : 'text-[#aaaaaa] hover:text-white'"
          >
            {{ category.label }}
          </button>
        </div>
      </nav>

      <!-- 添加按钮 -->
      <div class="p-4 border-t border-[#272727]">
        <button
          @click="showAddDialog = true"
          class="w-full px-4 py-2 bg-[#cc0000] text-white rounded-lg hover:bg-[#aa0000] transition-colors flex items-center justify-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          添加播客
        </button>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部搜索栏 -->
      <div class="p-4 border-b border-[#272727]">
        <SearchBar 
          @search="handleSearch" 
          ref="searchBar"
          placeholder="索播客..."
        />
      </div>

      <!-- 内容区域 -->
      <div class="flex-1 overflow-y-auto scrollbar-hide p-6">
        <!-- 正在收听 -->
        <section v-if="currentView === 'listening' && listening.length > 0" class="mb-8">
          <h2 class="text-xl font-bold mb-4">正在收听</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            <PodcastCard
              v-for="podcast in listening"
              :key="podcast.id"
              :podcast="podcast"
              :isPlaying="currentPodcast?.id === podcast.id"
              :progress="podcast.progress"
              @click="handlePodcastSelect(podcast)"
            />
          </div>
        </section>

        <!-- 最近更新 -->
        <section v-if="currentView === 'recent'" class="mb-8">
          <h2 class="text-xl font-bold mb-4">最近更新</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            <PodcastCard
              v-for="podcast in recentlyUpdated"
              :key="podcast.id"
              :podcast="podcast"
              :isPlaying="currentPodcast?.id === podcast.id"
              @click="handlePodcastSelect(podcast)"
            />
          </div>
        </section>

        <!-- 所有播客 -->
        <section>
          <h2 class="text-xl font-bold mb-4">
            {{ currentView === 'all' ? '所有播客' : getCategoryLabel(activeCategory) }}
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            <PodcastCard
              v-for="podcast in filteredPodcasts"
              :key="podcast.id"
              :podcast="podcast"
              :isPlaying="currentPodcast?.id === podcast.id"
              @click="handlePodcastSelect(podcast)"
            />
          </div>
        </section>
      </div>
    </div>

    <!-- 添加播客对话框 -->
    <AddPodcastDialog
      :show="showAddDialog"
      @close="showAddDialog = false"
      @added="handlePodcastAdded"
    />

    <!-- 播客详情抽屉 -->
    <PodcastDrawer
      v-if="selectedPodcast"
      :podcast="selectedPodcast"
      :isOpen="!!selectedPodcast"
      @close="selectedPodcast = null"
      @play="handleEpisodeClick"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, defineComponent, markRaw, inject } from 'vue';
import SearchBar from '../components/SearchBar.vue';
import PodcastCard from '../components/PodcastCard.vue';
import AddPodcastDialog from '../components/AddPodcastDialog.vue';
import PodcastDrawer from '../components/PodcastDrawer.vue';
import { usePodcasts } from '../composables/usePodcasts';
import useCustomToast from '../composables/useToast';
import axios from 'axios';
import GridIcon from '../components/icons/GridIcon.vue';
import PlayingIcon from '../components/icons/PlayingIcon.vue';
import ClockIcon from '../components/icons/ClockIcon.vue';

const searchBar = ref(null);
const currentPodcast = inject('currentPodcast');
const currentEpisode = inject('currentEpisode');
const isPlaying = inject('isPlaying');
const searchQuery = ref('');
const showAddDialog = ref(false);
const currentView = ref('all');
const { displayToast: showToast } = useCustomToast();

// 使用全局播放器方法
const playPodcast = inject('playPodcast');

const {
  podcasts,
  loading,
  error,
  hasMore,
  fetchPodcasts,
  resetPodcasts,
  fetchListening,
  updatePlayProgress
} = usePodcasts();

const categories = [
  { label: '全部', value: 'all' },
  { label: '新闻', value: 'news' },
  { label: '科技', value: 'tech' },
  { label: '商业', value: 'business' },
  { label: '文化', value: 'culture' },
  { label: '教育', value: 'education' },
  { label: '娱乐', value: 'entertainment' },
  { label: '音乐', value: 'music' },
  { label: '其他', value: 'others' }
];

const activeCategory = ref('all');
const listening = ref([]); // 正在收听的播客
const recentlyUpdated = computed(() => {
  return podcasts.value
    .slice()
    .sort((a, b) => new Date(b.last_update) - new Date(a.last_update))
    .slice(0, 6);
});

const filteredPodcasts = computed(() => {
  if (activeCategory.value === 'all') {
    return podcasts.value;
  }
  return podcasts.value.filter(podcast => podcast.category === activeCategory.value);
});

const getCategoryLabel = (value) => {
  return categories.find(c => c.value === value)?.label || '全部播客';
};

const handleSearch = (keyword) => {
  searchQuery.value = keyword;
  resetPodcasts();
  fetchPodcasts(keyword);
};

const handleScroll = (event) => {
  const { scrollTop, clientHeight, scrollHeight } = event.target;
  if (scrollHeight - scrollTop <= clientHeight + 100) {
    fetchPodcasts(searchQuery.value);
  }
};

const selectedPodcast = ref(null);

const handlePodcastSelect = async (podcast) => {
  selectedPodcast.value = podcast;
  // 如果需要，这里可以加载更多剧集
  try {
    const response = await axios.get(`/api/podcasts/channels/${podcast.id}/episodes`);
    selectedPodcast.value = {
      ...podcast,
      episodes: response.data
    };
  } catch (error) {
    console.error('Failed to load episodes:', error);
    showToast('加载剧集失败', 'error');
  }
};

const handleEpisodeClick = (episode) => {
  playPodcast(episode, selectedPodcast.value);
};

const handlePodcastAdded = () => {
  resetPodcasts();
  fetchPodcasts();
};

const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const formatDate = (date) => {
  if (!date) return '未知';
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

onMounted(async () => {
  fetchPodcasts();
  listening.value = await fetchListening();
});

// 导航项定义
const navItems = [
  { 
    id: 'all', 
    label: '所有播客',
    icon: GridIcon
  },
  { 
    id: 'listening', 
    label: '正在收听',
    icon: PlayingIcon
  },
  { 
    id: 'recent', 
    label: '最近更新',
    icon: ClockIcon
  }
];
</script>

<style scoped>
.podcasts-page {
  height: 100vh;
}

.scrollbar-hide {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style> 

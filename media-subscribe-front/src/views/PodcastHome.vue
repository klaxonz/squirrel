<template>
  <div class="podcast-home h-screen flex flex-col bg-[#0f0f0f] overflow-hidden">
    <!-- 顶部搜索和添加区域 -->
    <div class="flex items-center justify-between p-4">
      <SearchBar
        v-model="searchQuery"
        @search="handleSearch"
        placeholder="搜索播客..."
      />
      <button
        @click="showAddPodcastModal"
        class="ml-4 inline-flex items-center h-9 whitespace-nowrap rounded-full bg-[#272727] hover:bg-[#3f3f3f] transition-colors duration-200"
      >
        <div class="flex items-center px-3">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          <span class="text-white text-[14px] ml-2">添加播客</span>
        </div>
      </button>
    </div>

    <!-- 主要内容区域 -->
    <div class="flex-grow overflow-hidden">
      <div class="flex h-full">
        <!-- 左侧订阅频道列表 -->
        <div class="w-[320px] flex-shrink-0 border-r border-[#272727] overflow-y-auto">
          <div class="p-4">
            <h2 class="text-white text-lg font-medium mb-4">订阅频道</h2>
            <div class="space-y-3">
              <div
                v-for="channel in channels"
                :key="channel.id"
                class="flex items-center gap-3 p-2 rounded-lg hover:bg-[#272727] cursor-pointer transition-colors"
                @click="goToChannel(channel.id)"
              >
                <img
                  :src="channel.cover_url"
                  :alt="channel.title"
                  class="w-12 h-12 rounded object-cover"
                  referrerpolicy="no-referrer"
                />
                <div class="flex-grow min-w-0">
                  <h3 class="text-white text-sm font-medium line-clamp-1">{{ channel.title }}</h3>
                  <p class="text-[#aaaaaa] text-xs mt-1">{{ channel.total_count || 0 }} 集</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧最新剧集列表 -->
        <div class="flex-grow flex flex-col overflow-hidden">
          <!-- 固定的标题 -->
          <h2 class="text-white text-lg font-medium p-4">最新剧集</h2>
          
          <!-- 可滚动的列表区域 -->
          <div class="flex-grow overflow-y-auto scrollbar-hide" @scroll="handleScroll">
            <div class="p-4 pt-0 space-y-3">
              <div
                v-for="episode in episodes"
                :key="episode.id"
                class="flex items-center gap-4 p-3 rounded-lg bg-[#1a1a1a] hover:bg-[#272727] cursor-pointer transition-colors"
                @click="playEpisode(episode)"
              >
                <img
                  :src="episode.cover_url || episode.channel_cover_url"
                  :alt="episode.title"
                  class="w-16 h-16 rounded object-cover"
                  referrerpolicy="no-referrer"
                />
                <div class="flex-grow min-w-0">
                  <h3 class="text-white text-sm font-medium line-clamp-1">{{ episode.title }}</h3>
                  <p class="text-[#aaaaaa] text-xs mt-1 line-clamp-2">{{ episode.description }}</p>
                  <div class="flex items-center gap-2 mt-2 text-xs text-[#aaaaaa]">
                    <span>{{ episode.channel_title }}</span>
                    <span>·</span>
                    <span>{{ formatDuration(episode.duration) }}</span>
                    <span>·</span>
                    <span>{{ formatDate(episode.published_at) }}</span>
                  </div>
                </div>
              </div>

              <!-- 加载状态和无更多数据提示 -->
              <div v-if="episodeLoading" class="flex justify-center py-4">
                <div class="animate-spin rounded-full h-6 w-6 border-2 border-[#cc0000] border-t-transparent"></div>
              </div>
              
              <div v-if="noMoreEpisodes && episodes.length > 0" class="text-[#aaaaaa] text-sm text-center py-4">
                没有更多剧集了
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加播客模态框 -->
    <Teleport to="body">
      <div
        v-if="showModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showModal = false"
      >
        <div class="bg-[#282828] p-6 rounded-lg w-full max-w-md">
          <h2 class="text-xl font-medium text-white mb-4">添加播客</h2>
          <div class="mb-4">
            <input
              v-model="rssUrl"
              type="text"
              placeholder="输入播客 RSS 地址"
              class="w-full px-4 py-2 bg-[#181818] text-white rounded-lg border border-[#383838] focus:border-[#909090] outline-none"
              @keyup.enter="subscribePodcast"
            />
          </div>
          <div class="flex justify-end gap-3">
            <button
              @click="showModal = false"
              class="px-4 py-2 text-white hover:bg-[#383838] rounded-full transition-colors"
            >
              取消
            </button>
            <button
              @click="subscribePodcast"
              class="px-4 py-2 bg-[#cc0000] text-white rounded-full hover:bg-[#990000] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="loading || !rssUrl"
            >
              {{ loading ? '订阅中...' : '订阅' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 加载状态 -->
    <div v-if="loading && !channels.length" class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-[#cc0000] border-t-transparent"></div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && !channels.length" class="flex flex-col items-center justify-center p-8 text-[#aaaaaa]">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
      <p class="text-lg">还没有订阅任何播客</p>
      <button
        @click="showAddPodcastModal"
        class="mt-4 px-4 py-2 text-white hover:bg-[#383838] rounded-full transition-colors"
      >
        立即添加
      </button>
    </div>

    <!-- 添加加载状态和无更多数据提示 -->
    <div v-if="loading" class="flex justify-center py-4">
      <div class="animate-spin rounded-full h-6 w-6 border-2 border-[#cc0000] border-t-transparent"></div>
    </div>
    
    <div v-if="noMoreData && channels.length > 0" class="text-[#aaaaaa] text-sm text-center py-4">
      没有更多播客了
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue';
import { useRouter } from 'vue-router';
import SearchBar from '../components/SearchBar.vue';
import useCustomToast from '../composables/useToast';
import axios from '../utils/axios';

const router = useRouter();
const { displayToast } = useCustomToast();

const searchQuery = ref('');
const channels = ref([]);
const showModal = ref(false);
const rssUrl = ref('');
const loading = ref(false);
const page = ref(1);
const pageSize = ref(20);
const noMoreData = ref(false);
const showEmptyState = ref(false);

// 添加最新剧集相关的状态
const episodes = ref([]);
const episodePage = ref(1);
const episodePageSize = ref(20);
const episodeLoading = ref(false);
const noMoreEpisodes = ref(false);

const loadChannels = async () => {
  try {
    loading.value = true;
    const response = await axios.get('/api/podcasts/channels', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        query: searchQuery.value
      }
    });
    
    // 使用新的响应格式
    channels.value = response.data.items;
    noMoreData.value = !response.data.has_more;
    
    // 如果是第一页且没有数据，显示空状态
    if (page.value === 1 && channels.value.length === 0) {
      showEmptyState.value = true;
    } else {
      showEmptyState.value = false;
    }
    
  } catch (error) {
    displayToast(error.response?.data?.detail || '加载失败', { type: 'error' });
  } finally {
    loading.value = false;
  }
};

// 添加加载更多方法
const loadMore = async () => {
  if (loading.value || noMoreData.value) return;
  
  page.value++;
  try {
    loading.value = true;
    const response = await axios.get('/api/podcasts/channels', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        query: searchQuery.value
      }
    });
    
    // 追加新数据
    channels.value = [...channels.value, ...response.data.items];
    noMoreData.value = !response.data.has_more;
    
  } catch (error) {
    page.value--; // 加载失败，恢复页码
    displayToast(error.response?.data?.detail || '加载失败', { type: 'error' });
  } finally {
    loading.value = false;
  }
};

// 加载最新剧集
const loadLatestEpisodes = async (isLoadMore = false) => {
  if (episodeLoading.value || (isLoadMore && noMoreEpisodes.value)) return;

  try {
    episodeLoading.value = true;
    const response = await axios.get('/api/podcasts/episodes/latest', {
      params: {
        page: isLoadMore ? episodePage.value : 1,
        page_size: episodePageSize.value
      }
    });

    if (isLoadMore) {
      episodes.value = [...episodes.value, ...response.data.items];
      episodePage.value++;
    } else {
      episodes.value = response.data.items;
      episodePage.value = 2;
    }
    
    noMoreEpisodes.value = !response.data.has_more;
  } catch (error) {
    displayToast('加载最新剧集失败', { type: 'error' });
  } finally {
    episodeLoading.value = false;
  }
};

// 修改滚动处理方法
const handleScroll = (event) => {
  const target = event.target;
  const { scrollHeight, scrollTop, clientHeight } = target;
  
  // 当距离底部小于 100px 时加载更多
  if (scrollHeight - scrollTop - clientHeight < 100) {
    loadLatestEpisodes(true);
  }
};

// 搜索时重置状态
const handleSearch = () => {
  page.value = 1;
  channels.value = [];
  noMoreData.value = false;
  loadChannels();
};

const showAddPodcastModal = () => {
  showModal.value = true;
  rssUrl.value = '';
};

const subscribePodcast = async () => {
  if (!rssUrl.value) {
    displayToast('请输入RSS地址');
    return;
  }

  loading.value = true;
  try {
    await axios.post('/api/podcasts/channels/subscribe', null, {
      params: { rss_url: rssUrl.value }
    });
    displayToast('订阅成功');
    showModal.value = false;
    rssUrl.value = '';
    loadChannels();
  } catch (error) {
    displayToast(error.response?.data?.detail || '订阅失败', { type: 'error' });
  } finally {
    loading.value = false;
  }
};

const goToChannel = (channelId) => {
  router.push(`/podcasts/channel/${channelId}`);
};

// 添加格式化函数
const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return `${hours ? hours + ':' : ''}${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const formatDate = (date) => {
  if (!date) return '';
  const d = new Date(date);
  const now = new Date();
  const diff = now - d;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;
  return `${Math.floor(days / 365)}年前`;
};

// 添加播放控制
const playPodcast = inject('playPodcast');

const playEpisode = (episode) => {
  // 需要从后端获取完整的频道信息
  const channel = channels.value.find(c => c.id === episode.channel_id);
  playPodcast(episode, channel);
};

onMounted(() => {
  loadChannels();
  loadLatestEpisodes();
});
</script>

<style scoped>
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

/* 添加滚动条隐藏样式 */
.scrollbar-hide {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.scrollbar-hide::-webkit-scrollbar {
  display: none; /* Chrome, Safari and Opera */
}
</style> 
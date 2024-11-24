<template>
  <div class="podcast-channel h-screen flex flex-col bg-[#0f0f0f]">
    <!-- 固定的头部区域 -->
    <div class="flex-shrink-0">
      <!-- 频道头部信息 -->
      <div class="channel-header">
        <!-- 频道信息 -->
        <div class="pt-6 px-6">
          <div class="flex items-start gap-6">
            <img
              :src="channel?.cover_url || '/podcast-placeholder.jpg'"
              :alt="channel?.title"
              class="w-32 h-32 rounded-lg shadow-lg object-cover flex-shrink-0"
              referrerpolicy="no-referrer"
            />
            <div class="flex-grow pt-2">
              <h1 class="text-2xl font-medium text-white mb-2">{{ channel?.title }}</h1>
              <p class="text-[#aaaaaa] text-sm mb-4 line-clamp-2">{{ channel?.description }}</p>
              <div class="flex items-center gap-4">
                <button
                  @click="handleSubscriptionClick"
                  :class="[
                    'px-4 py-2 rounded-full text-sm font-medium transition-colors duration-200',
                    isSubscribed 
                      ? 'bg-[#272727] hover:bg-[#3f3f3f] text-white'
                      : 'bg-white hover:bg-gray-100 text-black'
                  ]"
                >
                  {{ isSubscribed ? '已订阅' : '订阅' }}
                </button>
                <span class="text-[#aaaaaa] text-sm">{{ channel?.total_count || 0 }} 集</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 可滚动的剧集列表区域 -->
    <div 
      class="flex-grow overflow-y-auto scrollbar-hide mt-6 px-6" 
      @scroll="handleScroll"
      ref="scrollContainer"
    >
      <div class="episodes-list space-y-3 pb-24">
        <!-- 剧集卡片 -->
        <div
          v-for="episode in episodes"
          :key="episode.id"
          class="episode-card bg-[#1a1a1a] hover:bg-[#282828] transition-colors cursor-pointer group py-4 rounded-lg"
          @click="playEpisode(episode)"
        >
          <div class="flex items-center gap-4 px-4">
            <img
              :src="episode.cover_url || channel?.cover_url"
              :alt="episode.title"
              class="w-16 h-16 rounded-sm object-cover flex-shrink-0"
              referrerpolicy="no-referrer"
            />
            <div class="flex-grow min-w-0">
              <div class="flex flex-col">
                <h3 class="text-white text-base line-clamp-1 mb-1">{{ episode.title }}</h3>
                <p class="text-[#aaaaaa] text-sm line-clamp-2 mb-1">{{ episode.description }}</p>
                <div class="flex items-center text-xs text-[#aaaaaa]">
                  <span>{{ formatDuration(episode.duration) }}</span>
                  <span class="mx-2">·</span>
                  <span>{{ formatDate(episode.published_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 加载更多提示 -->
        <div v-if="loading" class="flex justify-center py-4">
          <div class="animate-spin rounded-full h-6 w-6 border-2 border-[#cc0000] border-t-transparent"></div>
        </div>

        <!-- 无更多数据提示 -->
        <div v-if="noMoreData" class="text-[#aaaaaa] text-sm text-center py-4">
          没有更多剧集了
        </div>
      </div>
    </div>

    <!-- 播放器 -->
    <audio-player
      v-if="currentEpisode"
      :episode="currentEpisode"
      :channel="channel"
      @progress="updateProgress"
      @ended="onEpisodeEnded"
      class="fixed bottom-0 left-0 right-0"
    />

    <!-- 添加确认对话框 -->
    <Teleport to="body">
      <div
        v-if="showUnsubscribeConfirm"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="showUnsubscribeConfirm = false"
      >
        <div class="bg-[#282828] p-6 rounded-lg w-full max-w-md">
          <h2 class="text-xl font-medium text-white mb-4">取消订阅</h2>
          <p class="text-[#aaaaaa] mb-6">
            取消订阅后，将清除所有数据，包括播放记录。确定要取消订阅吗？
          </p>
          <div class="flex justify-end gap-3">
            <button
              @click="showUnsubscribeConfirm = false"
              class="px-4 py-2 text-white hover:bg-[#383838] rounded-full transition-colors"
            >
              保持订阅
            </button>
            <button
              @click="handleUnsubscribe"
              class="px-4 py-2 bg-[#cc0000] text-white rounded-full hover:bg-[#990000] transition-colors"
            >
              取消订阅
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, inject } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import useCustomToast from '../composables/useToast';
import axios from '../utils/axios';

const route = useRoute();
const router = useRouter();
const { displayToast } = useCustomToast();

const channel = ref(null);
const episodes = ref([]);
const currentEpisode = ref(null);
const isSubscribed = ref(false);
const showUnsubscribeConfirm = ref(false);

// 格式化工具函数
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

// 添加分页相关的响应式变量
const page = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const noMoreData = ref(false);
const scrollContainer = ref(null);

// 加载数据
const loadChannel = async () => {
  try {
    const response = await axios.get(`/api/podcasts/channels/${route.params.id}`);
    channel.value = response.data;
    isSubscribed.value = response.data.is_subscribed;
  } catch (error) {
    displayToast('加载播客信息失败', { type: 'error' });
  }
};

// 修改加载剧集的方法
const loadEpisodes = async (isLoadMore = false) => {
  if (loading.value || (isLoadMore && noMoreData.value)) return;

  try {
    loading.value = true;
    const response = await axios.get(`/api/podcasts/channels/${route.params.id}/episodes`, {
      params: {
        page: isLoadMore ? page.value : 1,
        page_size: pageSize.value
      }
    });

    if (isLoadMore) {
      episodes.value = [...episodes.value, ...response.data];
      noMoreData.value = response.data.length < pageSize.value;
      page.value++;
    } else {
      episodes.value = response.data;
      noMoreData.value = response.data.length < pageSize.value;
      page.value = 2;
    }
  } catch (error) {
    displayToast('加载剧集列表失败', { type: 'error' });
  } finally {
    loading.value = false;
  }
};

// 添加滚动处理方法
const handleScroll = () => {
  if (!scrollContainer.value) return;
  
  const { scrollTop, scrollHeight, clientHeight } = scrollContainer.value;
  // 当距离底部小于 100px 时加载更多
  if (scrollHeight - scrollTop - clientHeight < 100) {
    loadEpisodes(true);
  }
};

// 订阅相关
const handleSubscriptionClick = () => {
  if (isSubscribed.value) {
    showUnsubscribeConfirm.value = true;
  } else {
    toggleSubscription();
  }
};

const toggleSubscription = async () => {
  try {
    await axios.post(`/api/podcasts/channels/${route.params.id}/subscribe`, {
      subscribed: true
    });
    isSubscribed.value = true;
    displayToast('订阅成功');
  } catch (error) {
    displayToast('订阅失败', { type: 'error' });
  }
};

const handleUnsubscribe = async () => {
  try {
    await axios.delete(`/api/podcasts/channels/${route.params.id}/subscription`);
    isSubscribed.value = false;
    showUnsubscribeConfirm.value = false;
    displayToast('已取消订阅');
    // 取消订阅后返回上一页
    router.back();
  } catch (error) {
    displayToast(error.response?.data?.detail || '取消订阅失败', { type: 'error' });
  }
};

// 播放控制
const playPodcast = inject('playPodcast');

const playEpisode = (episode) => {
  playPodcast(episode, channel.value);
};

const updateProgress = async (position) => {
  if (!currentEpisode.value) return;
  try {
    await axios.post(`/api/podcasts/episodes/${currentEpisode.value.id}/progress`, {
      position: Math.floor(position)
    });
  } catch (error) {
    console.error('Failed to update progress:', error);
  }
};

const onEpisodeEnded = async () => {
  if (!currentEpisode.value) return;
  try {
    await axios.post(`/api/podcasts/episodes/${currentEpisode.value.id}/mark-read`, {
      is_read: true
    });
    loadEpisodes(); // 重新加载列表以更新状态
  } catch (error) {
    console.error('Failed to mark episode as read:', error);
  }
};

// 生命周期
onMounted(async () => {
  await loadChannel();
  await loadEpisodes();

  // 点击外部关闭下拉菜单
  document.addEventListener('click', (e) => {
    const target = e.target;
    if (!target.closest('.relative')) {
      showDropdown.value = false;
    }
  });
});
</script>

<style scoped>
/* 隐藏滚动条但保持可滚动 */
.scrollbar-hide {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.scrollbar-hide::-webkit-scrollbar {
  display: none; /* Chrome, Safari and Opera */
}

/* 让列表居左 */
.episodes-list {
  margin: 0 auto;
  margin-left: 0;
}

/* 保持原有的其他样式 */
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

svg {
  transition: transform 0.2s ease;
}
</style> 
<template>
  <div class="subscribed-page flex flex-col h-full bg-[#0f0f0f] text-white">
    <!-- 顶部操作栏 - 对齐全部视频页的标签样式 -->
    <div class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between py-3">
        <TabBar
          v-model="activeTab"
          :tabs="tabsWithCounts"
          class="custom-tab-bar flex-grow"
          @tab-dblclick="handleTabDoubleClick"
        />
        <div class="flex items-center">
          <NsfwFilter v-model="nsfw" class="ml-2" @update:modelValue="handleNsfwChange" />
          <RefreshButton
            class="ml-2"
            :loading="isRefreshing"
            title="刷新"
            aria-label="刷新"
            @click="refreshList"
          />
          <button
            class="ml-2 px-3 py-1.5 min-w-[100px] bg-white/10 hover:bg-white/15 text-white rounded-full flex items-center justify-center transition-colors whitespace-nowrap text-xs font-medium"
            @click="showAddDialog = true"
          >
            <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path clip-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a 1 1 0 110 2h-5v5a 1 1 0 11-2 0v-5H4a 1 1 0 110-2h5V4a 1 1 0 011-1z" fill-rule="evenodd" />
            </svg>
            <span class="ml-1">添加订阅</span>
          </button>
        </div>
      </div>
    </div>

    <div
      ref="scrollContainer"
      class="channel-container pt-4 flex-grow overflow-y-auto"
      @scroll="handleScrollPosition"
    >
      <div class="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8">
        <!-- 频道列表 -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-3">
          <div v-for="subscription in subscriptions" :key="subscription.id"
               class="channel-item bg-[#202020] rounded-lg overflow-hidden hover:bg-[#303030] transition-all duration-200 relative group"
               :class="{ 'is-refreshing': isResetting }"
               @click="getSubscriptionVideos(subscription.id)"
          >
            <div class="flex justify-center items-center p-3 bg-[#181818]">
              <div class="relative w-14 h-14">
                <img
                  :alt="subscription.name"
                  :src="subscription.avatar"
                  class="w-full h-full rounded-full object-cover ring-1 ring-[#303030] transition-transform duration-300 group-hover:scale-105"
                  referrerpolicy="no-referrer"
                  @error="handleImageError($event)"
                />
                <div class="absolute -inset-0.5 bg-gradient-to-b from-transparent to-[#181818] opacity-20 rounded-full"></div>
              </div>
            </div>

            <div class="p-2 text-center">
              <h3 class="text-xs font-semibold truncate text-white">{{ subscription.name }}</h3>
              <p class="text-[10px] text-[#aaa] mt-0.5">
                总视频: {{ subscription.total_videos }} | 已解析: {{ subscription.total_extract }}
              </p>
              <p class="text-[10px] text-[#aaa] mt-0.5">订阅时间: {{ formatDate(subscription.created_at) }}</p>
            </div>

            <button class="absolute top-1 right-1 p-1 bg-black bg-opacity-50 rounded-full hover:bg-opacity-75 transition-colors duration-200 opacity-0 group-hover:opacity-100"
                    @click.stop="openSettings(subscription)">
              <svg class="h-3.5 w-3.5 text-white" fill="currentColor" viewBox="0 0 20 20"
                   xmlns="http://www.w3.org/2000/svg">
                <path clip-rule="evenodd"
                      d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                      fill-rule="evenodd"/>
              </svg>
            </button>

            <!-- YouTube风格的更新状态指示器 -->
            <div v-if="getRefreshState(subscription.id).isRefreshing"
                 class="absolute top-1.5 left-1.5 bg-white/10 text-white/80 text-[10px] px-1.5 py-0.5 rounded-md">
              <span>{{ getYouTubeStyleStatusText(getRefreshState(subscription.id).status, getRefreshState(subscription.id).phase) }}</span>
            </div>
          </div>
        </div>

        <!-- 加载更多按钮 -->
        <div
            v-if="!allLoaded"
            ref="loadingTrigger"
            class="mt-4 mb-4 text-center loading-trigger h-20 flex items-center justify-center"
        >
          <div v-if="loading" class="flex items-center justify-center space-x-2">
            <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-[#cc0000] rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
          </div>
        </div>

        <!-- 全部加载完毕 -->
        <div v-if="allLoaded" class="mt-4 mb-4 text-center text-[#aaa]">
          <p>已经到底啦</p>
        </div>
      </div>
    </div>

    <!-- 设置模态框 -->
    <div v-if="showSettings" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
         @click.self="closeSettings">
      <div class="bg-[#212121] rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4 text-white">{{ selectedSubscription.name }} 设置</h2>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <span class="text-white">标记为敏感内容</span>
            <ToggleSwitch v-model="selectedSubscription.is_nsfw" @update:modelValue="updateNsfwStatus"/>
          </div>

          <!-- 手动更新按钮 -->
          <div class="space-y-3">
            <button
              class="w-full py-2 bg-[#404040] text-white rounded-lg hover:bg-[#505050] disabled:bg-[#303030] disabled:cursor-not-allowed transition-colors duration-200 text-sm"
              :disabled="getRefreshState(selectedSubscription.id).isRefreshing"
              @click="handleRefreshSubscription(selectedSubscription.id)"
            >
              <span v-if="getRefreshState(selectedSubscription.id).isRefreshing">
                {{ getStatusText(getRefreshState(selectedSubscription.id).status, getRefreshState(selectedSubscription.id).phase) }}
              </span>
              <span v-else>手动更新</span>
            </button>

            <!-- 进度不再内嵌，转移到全局“同步中心”与卡片角标展示 -->

            <!-- 错误状态和重试 -->
            <div v-if="getRefreshState(selectedSubscription.id).status === 'failed'" class="text-xs">
              <p class="text-red-400 mb-2">{{ getRefreshState(selectedSubscription.id).lastError || '更新失败' }}</p>
              <button
                class="w-full py-1.5 bg-[#505050] text-white rounded hover:bg-[#606060] transition-colors duration-200"
                @click="handleRetryRefresh(selectedSubscription.id)"
              >
                重试更新
              </button>
            </div>
          </div>

          <button
            :disabled="getRefreshState(selectedSubscription.id).isRefreshing"
            :class="[
              'w-full py-2 text-white rounded-lg transition-colors duration-200 text-sm',
              getRefreshState(selectedSubscription.id).isRefreshing
                ? 'bg-[#303030] cursor-not-allowed'
                : 'bg-[#cc0000] hover:bg-[#990000]'
            ]"
            @click="unsubscribe(selectedSubscription.id)"
          >
            取消订阅
          </button>
          <p v-if="unsubscribeError" class="mt-2 text-xs text-red-400">{{ unsubscribeError }}</p>
        </div>
        <button class="mt-6 w-full py-2 bg-[#606060] text-white rounded-lg hover:bg-[#808080] transition-colors duration-200 text-sm font-medium"
                @click="closeSettings">
          关闭
        </button>
      </div>
    </div>

    <!-- 添加频道对话框 -->
    <AddChannelDialog
      :show="showAddDialog"
      @added="handleChannelAdded"
      @close="showAddDialog = false"
    />


  </div>

</template>

<script setup>
import {nextTick, onMounted, onUnmounted, ref, watch, inject} from 'vue';
import RefreshButton from '../components/RefreshButton.vue';
import ToggleSwitch from '../components/ToggleSwitch.vue';
import {useRouter} from "vue-router";
import AddChannelDialog from '../components/AddChannelDialog.vue';
import NsfwFilter from '../components/NsfwFilter.vue';
import TabBar from '../components/TabBar.vue';

import {formatDate} from '../utils/dateFormat';
import {useScrollPosition} from '../composables/useScrollPosition';
import {useSubscriptionRefresh} from '../composables/useSubscriptionRefresh';
import {useSubscriptionApi} from '../composables/useSubscriptionApi';

const router = useRouter();

const isRefreshing = ref(false);
const isResetting = ref(false);

const emitter = inject('emitter');

// 滚动位置保持
const { scrollContainer, handleScroll: handleScrollPosition, restoreScrollPosition } = useScrollPosition('subscribed-page');

const subscriptions = ref([]);
const loading = ref(false);
const allLoaded = ref(false);
const currentPage = ref(1);
const searchQuery = ref('');
const nsfw = ref('all');
const activeTab = ref('all');
const tabsWithCounts = ref([
  { value: 'all', label: '全部', count: 0 },
  { value: 'unread', label: '未读', count: 0 },
  { value: 'read', label: '已读', count: 0 },
  { value: 'preview', label: '预告', count: 0 },
  { value: 'liked', label: '喜欢', count: 0 }
]);

const showSettings = ref(false);
const selectedSubscription = ref(null);

const observer = ref(null);
const loadingTrigger = ref(null);



const showAddDialog = ref(false);
const unsubscribeError = ref('');

// API功能
const {
  getSubscriptions: apiGetSubscriptions,
  unsubscribe: apiUnsubscribe,
  updateNsfwStatus: apiUpdateNsfwStatus
} = useSubscriptionApi();

// 订阅更新功能
const {
  getRefreshState,
  triggerRefresh,
  retryRefresh,
  getStatusText,
  getProgressPercentage,
  cleanup: cleanupRefresh
} = useSubscriptionRefresh();


const setupIntersectionObserver = () => {
  observer.value = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loading.value && !allLoaded.value) {
          loadMore();
        }
      },
      {
        root: scrollContainer.value,
        rootMargin: '100px',
        threshold: 0
      }
  );

  // 确保在组件挂载后观察loading trigger
  if (loadingTrigger.value) {
    observer.value.observe(loadingTrigger.value);
  }
};

const loadSubscriptions = async () => {
  if (loading.value || allLoaded.value) return;

  loading.value = true;

  const result = await apiGetSubscriptions({
    query: searchQuery.value,
    nsfw: nsfw.value,
    page: currentPage.value,
    page_size: 100
  });

  if (result.success) {
    const newSubscriptions = result.data.data;
    const mapped = newSubscriptions.map(subscription => ({
      ...subscription,
      total_videos: subscription.total_videos || 0,
      total_extract: subscription.total_extract || 0
    }));

    if (currentPage.value === 1) {
      // 首次页刷新：保留旧DOM，数据返回后整体替换
      subscriptions.value = mapped;
    } else {
      // 分页：追加且去重
      const existingIds = new Set(subscriptions.value.map(s => s.id));
      const deduped = mapped.filter(s => !existingIds.has(s.id));
      subscriptions.value = [...subscriptions.value, ...deduped];
    }

    currentPage.value++;
    if (newSubscriptions.length < 20) {
      allLoaded.value = true;
    }

    nextTick(() => {
      if (loadingTrigger.value && observer.value) {
        observer.value.observe(loadingTrigger.value);
      }
      // 数据加载完成后恢复滚动位置
      restoreScrollPosition();
    });
  }

  loading.value = false;
};


// 订阅页：键盘 R 刷新 + 页面切回自动刷新
const lastRefreshedAt = ref(Date.now());
const VISIBILITY_REFRESH_THRESHOLD_MS = 5 * 60 * 1000;

const MIN_SPIN_MS = 800;
const spinTimer = ref(null);
const spinStartAt = ref(0);
const clearSpinTimer = () => {
  if (spinTimer.value) {
    clearTimeout(spinTimer.value);
    spinTimer.value = null;
  }
};


const handleKeyDown = (e) => {
  const target = e.target;
  if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if ((e.key === 'r' || e.key === 'R') && !e.repeat) {
    e.preventDefault();
    refreshList();
  }
};

const handleVisibilityChange = () => {
  if (!document.hidden) {
    if (Date.now() - lastRefreshedAt.value > VISIBILITY_REFRESH_THRESHOLD_MS) {
      refreshList();
    }
  }
};

// 处理全局搜索事件

const refreshList = async () => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value);
  }
  clearSpinTimer();
  isRefreshing.value = true;
  isResetting.value = true;
  spinStartAt.value = Date.now();
  currentPage.value = 1;
  allLoaded.value = false;
  try {
    await loadSubscriptions();
  } finally {
    const elapsed = Date.now() - spinStartAt.value;
    const remain = Math.max(0, MIN_SPIN_MS - elapsed);
    clearSpinTimer();
    spinTimer.value = setTimeout(() => {
      isRefreshing.value = false;
      isResetting.value = false;
      lastRefreshedAt.value = Date.now();
      clearSpinTimer();
    }, remain);
  }
};

const handleGlobalSearch = (query) => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value);
  }
  searchQuery.value = query;
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadSubscriptions().then(() => {
    // 搜索后恢复滚动位置
    nextTick(() => {
      restoreScrollPosition();
    });
    isRefreshing.value = false;

  });
};

// NSFW 筛选变更：重置并重新加载
const handleNsfwChange = () => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value);
  }
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadSubscriptions();
};

const loadMore = () => {
  loadSubscriptions();
};

// 顶部标签：双击刷新订阅列表
const handleTabDoubleClick = (tab) => {
  if (tab === activeTab.value) {
    refreshList();
  }
};

// 切换顶部标签时，跳转到对应的全部视频页
watch(() => activeTab.value, (newVal) => {
  const target = `/videos/${newVal}`;
  if (router.currentRoute.value.fullPath !== target) {
    router.push(target);
  }
});

const openSettings = (subscription) => {
  selectedSubscription.value = {...subscription};
  // 向全局刷新中心补充元数据
  try {
    const { setSubscriptionMeta } = useSubscriptionRefresh();
    setSubscriptionMeta(subscription.id, { name: subscription.name, avatar: subscription.avatar });
  } catch (e) {}
  showSettings.value = true;
};

const closeSettings = () => {
  showSettings.value = false;
  selectedSubscription.value = null;
  unsubscribeError.value = '';
};

const unsubscribe = async (subscriptionId) => {
  unsubscribeError.value = '';

  const result = await apiUnsubscribe(subscriptionId);

  if (result.success) {
    subscriptions.value = subscriptions.value.filter(subscription => subscription.id !== subscriptionId);
    closeSettings();
  } else if (!result.cancelled) {
    unsubscribeError.value = result.error || '取消订阅失败';
  }
};

const getSubscriptionVideos = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`);
}



const handleImageError = (event) => {
  event.target.src = '/squirrel-icon.svg';
};

const handleChannelAdded = () => {
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadSubscriptions();
};

const updateNsfwStatus = async (isNsfw) => {
  const result = await apiUpdateNsfwStatus(selectedSubscription.value.id, isNsfw);

  if (result.success) {
    // 立即更新本地状态
    const index = subscriptions.value.findIndex(s => s.id === selectedSubscription.value.id);
    if (index !== -1) {
      subscriptions.value[index].is_nsfw = isNsfw;
    }
  } else {
    // 回滚UI状态
    selectedSubscription.value.is_nsfw = !isNsfw;
  }
};

// 处理手动更新订阅
const handleRefreshSubscription = async (subscriptionId) => {
  await triggerRefresh(subscriptionId);
};

// 处理重试更新
const handleRetryRefresh = async (subscriptionId) => {
  await retryRefresh(subscriptionId);
};

// YouTube风格的状态文案
const getYouTubeStyleStatusText = (status, phase) => {
  if (status === 'queued') return '排队中';
  if (status === 'in_progress') {
    switch (phase) {
      case 'init': return '准备中';
      case 'fetching_feed': return '检查新内容';
      case 'calculating_delta': return '分析更新';
      case 'extracting': return '解析中';
      case 'finalizing': return '即将完成';
      default: return '更新中';
    }
  }
  if (status === 'completed') return '已完成';
  if (status === 'failed') return '更新失败';
  return '更新中';
};

// 格式化时间为"X分钟前开始"
const formatTimeAgo = (timeString) => {
  if (!timeString) return '';
  const now = new Date();
  const time = new Date(timeString);
  const diffInMinutes = Math.floor((now - time) / (1000 * 60));

  if (diffInMinutes < 1) return '刚刚开始';
  if (diffInMinutes < 60) return `${diffInMinutes}分钟前开始`;
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `${diffInHours}小时前开始`;
  return `${Math.floor(diffInHours / 24)}天前开始`;
};

onMounted(async () => {
  try {
    const api = useSubscriptionRefresh();
    await api.rehydrateFromServer();
  } catch (e) {}
  loadSubscriptions();
  nextTick(() => {
    setupIntersectionObserver();
  });

  // 监听全局搜索事件
  emitter.on('search:subscribed', handleGlobalSearch);

  // 键盘快捷键：R 刷新订阅列表
  window.addEventListener('keydown', handleKeyDown);
  // 页面可见性变化：切回且超过阈值时自动刷新
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

// 添加监听器以在内容变化时重新设置observer
watch(subscriptions, () => {
  nextTick(() => {
    if (observer.value && loadingTrigger.value) {
      observer.value.unobserve(loadingTrigger.value);
      observer.value.observe(loadingTrigger.value);
    }
  });
}, { deep: true });

onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect();
  }

  // 移除全局搜索事件监听
  emitter.off('search:subscribed', handleGlobalSearch);

  // 清理订阅更新相关资源
  cleanupRefresh();

  window.removeEventListener('keydown', handleKeyDown);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
</script>

<style scoped>
.subscribed-page {
  height: 100vh;
}

.channel-container {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.channel-container::-webkit-scrollbar {
  display: none;
}

.channel-item {
  transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.channel-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.channel-item img {
  transition: all 0.3s ease-in-out;
  backface-visibility: hidden;
}

.channel-item:hover img {
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
}

.channel-item > div:nth-child(2) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.channel-item .w-24 {
  filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
}
  /* 刷新图标旋转 */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin-anim { animation: spin 0.8s linear infinite; }

  /* 刷新蒙层，保留旧卡片 DOM，降低突变感 */
  .channel-item.is-refreshing::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.06), rgba(255,255,255,0));
    animation: shimmer 1.2s infinite;
    pointer-events: none;
    border-radius: inherit;
  }
  @keyframes shimmer { 0% { transform: translateX(-100%);} 100% { transform: translateX(100%);} }
</style>

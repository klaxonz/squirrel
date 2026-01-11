<template>
  <div class="subscribed-page flex flex-col h-full bg-bg-primary text-text-primary">
    <!-- 顶部操作栏 - 对齐全部视频页的标签样式 -->
    <div class="toolbar-container">
      <FeedToolbar
        :show-tabs="false"
        :tabs-with-counts="[]"
        :nsfw="nsfw"
        :site="site"
        :is-refreshing="isRefreshing"
        @update:nsfw="(v) => { nsfw = v; }"
        @update:site="(v) => { site = v; }"
        @refresh="refreshList"
      >
        <Button
          class="ml-2 whitespace-nowrap"
          size="xs"
          shape="pill"
          variant="secondary"
          @click="showAddDialog = true"
        >
          <PlusIcon class="h-4 w-4" />
          <span class="ml-1">添加订阅</span>
        </Button>
        <Button
          class="ml-2 whitespace-nowrap"
          size="xs"
          shape="pill"
          variant="danger"
          @click="showImportDialog = true"
        >
          <ArrowDownTrayIcon class="h-4 w-4" />
          <span class="ml-1">导入订阅</span>
        </Button>

      </FeedToolbar>
    </div>

    <div
      ref="scrollContainer"
      class="channel-container scrollbar-hide pt-0 flex-grow overflow-y-auto"
      @scroll="handleScrollPosition"
    >
      <div class="content-container" v-if="loadError">
        <InlineAlert
          :message="`加载失败：${loadError?.message || loadError}`"
          action-label="重试"
          @action="refreshList"
        />
      </div>
      <div class="content-container">
        <!-- 频道列表 -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-3">
          <div v-for="subscription in subscriptions" :key="subscription.id"
               class="channel-item bg-bg-card rounded-lg overflow-hidden hover:bg-bg-elevated transition-all duration-200 relative group cursor-pointer"

               :class="{ 'is-refreshing': isResetting }"
               @click="getSubscriptionVideos(subscription.id)"
          >
            <div class="flex justify-center items-center p-3 bg-bg-secondary">
              <div class="relative w-14 h-14">
                <img
                  :alt="subscription.name"
                  :src="getAvatarSrc(subscription.avatar, subscription.id)"
                  class="w-full h-full rounded-full object-cover ring-1 ring-border-primary transition-transform duration-300 group-hover:scale-105"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, subscription.id)"
                />
                <div class="absolute -inset-0.5 avatar-sheen opacity-20 rounded-full"></div>
              </div>
            </div>

            <div class="p-2 text-center">
              <div class="flex items-center justify-center gap-1 mb-0.5">
                <h3 class="text-xs font-semibold truncate text-text-primary">{{ subscription.name }}</h3>
                <span v-if="subscription.type === 'PLAYLIST'" 
                      class="text-2xs px-1 py-0.5 rounded bg-color-info/20 text-color-info whitespace-nowrap"
                      title="播放列表">
                  播放列表
                </span>
              </div>
              <p class="text-2xs text-text-muted mt-0.5">
                总视频: {{ subscription.total_videos }} | 已解析: {{ subscription.total_extract }}
              </p>
              <p class="text-2xs text-text-muted mt-0.5">订阅时间: {{ formatDate(subscription.created_at) }}</p>
            </div>

            <button class="settings-toggle absolute top-1 right-1 p-1 bg-bg-tertiary/50 rounded-full hover:bg-bg-tertiary/75 transition-colors duration-200 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100"
                    @click.stop="openSettings(subscription)">
              <svg class="h-3.5 w-3.5 text-text-primary" fill="currentColor" viewBox="0 0 20 20"
                   xmlns="http://www.w3.org/2000/svg">
                <path clip-rule="evenodd"
                      d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                      fill-rule="evenodd"/>
              </svg>
            </button>

            <!-- YouTube风格的更新状态指示器 -->
            <div v-if="getRefreshState(subscription.id).isRefreshing"
                 class="absolute top-1.5 left-1.5 bg-bg-elevated text-text-primary/80 text-2xs px-1.5 py-0.5 rounded-md">
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
            <div class="w-2 h-2 bg-color-error rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-color-error rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-color-error rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
          </div>
        </div>

        <!-- 全部加载完毕 -->
        <div v-if="allLoaded" class="mt-4 mb-4 text-center text-text-muted">
          <p>已经到底啦</p>
        </div>
      </div>
    </div>

    <!-- 设置模态框 -->
    <div v-if="showSettings" class="fixed inset-0 bg-overlay-dark-50 flex items-center justify-center z-50"
         @click.self="closeSettings">
      <div class="bg-bg-card border border-border-primary rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4 text-text-primary">{{ selectedSubscription.name }} 设置</h2>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <span class="text-text-primary">标记为敏感内容</span>
            <ToggleSwitch v-model="selectedSubscription.is_nsfw" @update:modelValue="updateNsfwStatus"/>
          </div>

          <!-- 手动更新按钮 -->
          <div class="space-y-3">
            <button
              class="w-full py-2 bg-bg-elevated text-text-primary rounded-lg hover:bg-bg-tertiary disabled:bg-bg-secondary disabled:cursor-not-allowed transition-colors duration-200 text-sm"
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
              <p class="text-color-error mb-2">{{ getRefreshState(selectedSubscription.id).lastError || '更新失败' }}</p>
              <button
                class="w-full py-1.5 bg-bg-elevated text-text-primary rounded hover:bg-bg-tertiary transition-colors duration-200"
                @click="handleRetryRefresh(selectedSubscription.id)"
              >
                重试更新
              </button>
            </div>
          </div>

          <button
            :disabled="getRefreshState(selectedSubscription.id).isRefreshing"
            :class="[
              'w-full py-2 text-text-primary rounded-lg transition-colors duration-200 text-sm',
              getRefreshState(selectedSubscription.id).isRefreshing
                ? 'bg-bg-secondary cursor-not-allowed'
                : 'bg-color-error hover:bg-color-error-hover'
            ]"
            @click="unsubscribe(selectedSubscription.id)"
          >
            取消订阅
          </button>
          <p v-if="unsubscribeError" class="mt-2 text-xs text-color-error">{{ unsubscribeError }}</p>
        </div>
        <button class="mt-6 w-full py-2 bg-bg-elevated text-text-primary rounded-lg hover:bg-bg-tertiary transition-colors duration-200 text-sm font-medium"
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

    <!-- 导入订阅对话框 -->
    <ImportSubscriptionDialog
      :show="showImportDialog"
      @close="showImportDialog = false"
      @imported="handleSubscriptionsImported"
    />

  </div>

</template>

<script setup>
import {nextTick, onMounted, onUnmounted, ref, watch, inject} from 'vue';       
import FeedToolbar from '../components/feed/FeedToolbar.vue';
import Button from '../components/common/Button.vue';
import InlineAlert from '../components/common/InlineAlert.vue';
import { PlusIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline';        
import ToggleSwitch from '../components/ToggleSwitch.vue';
import {useRouter} from "vue-router";
import { useRefreshTriggers } from '../composables/useRefreshTriggers';
import AddChannelDialog from '../components/AddChannelDialog.vue';
import ImportSubscriptionDialog from '../components/ImportSubscriptionDialog.vue';

import {formatDate} from '../utils/dateFormat';
import {useScrollPosition} from '../composables/useScrollPosition';
import {useSubscriptionRefresh} from '../composables/useSubscriptionRefresh';
import {useSubscriptionApi} from '../composables/useSubscriptionApi';
import { useFeedFilters } from '../composables/useFeedFilters';
import { useImageFallback } from '../composables/useImageFallback';

const router = useRouter();

const isRefreshing = ref(false);
const isResetting = ref(false);

const emitter = inject('emitter');

// 滚动位置保持
const { scrollContainer, handleScroll: handleScrollPosition, restoreScrollPosition } = useScrollPosition('subscribed-page');

const subscriptions = ref([]);
const loadError = ref(null);
const loading = ref(false);
const allLoaded = ref(false);
const currentPage = ref(1);
const searchQuery = ref('');
const { nsfw, site } = useFeedFilters();
// Removed tabs on Subscribed page
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();

const showSettings = ref(false);
const selectedSubscription = ref(null);

const observer = ref(null);
const loadingTrigger = ref(null);



const showAddDialog = ref(false);
const showImportDialog = ref(false);
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
    site: site.value,
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
  } else if (!result.cancelled) {
    loadError.value = result.error || '获取订阅列表失败';
  }

  loading.value = false;
};


// 订阅页：键盘 R 刷新 + 页面切回自动刷新
const MIN_SPIN_MS = 800;
const spinTimer = ref(null);
const spinStartAt = ref(0);
const clearSpinTimer = () => {
  if (spinTimer.value) {
    clearTimeout(spinTimer.value);
    spinTimer.value = null;
  }
};


useRefreshTriggers({ onRefresh: () => refreshList() });

// 处理全局搜索事件

const refreshList = async () => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value);
  }
  clearSpinTimer();
  isRefreshing.value = true;
  isResetting.value = true;
  loadError.value = null;
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
    nextTick(() => {
      restoreScrollPosition();
    });
    isRefreshing.value = false;
  });
};

// 监听筛选变化：重置并重新加载
watch([nsfw, site], async () => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value);
  }
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  await loadSubscriptions();
});

const loadMore = () => {
  loadSubscriptions();
};

// Removed tab interactions

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



const handleChannelAdded = () => {
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadSubscriptions();
};

const handleSubscriptionsImported = () => {
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

  // 键盘/可见性刷新改为 composable 统一管理
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

  // 键盘/可见性刷新由 composable 自动清理
});
</script>

<style scoped>
.subscribed-page {
  height: 100vh;
}

.toolbar-container,
.content-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding: 0 1rem;
  width: 100%;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding: 0 2rem;
  }
}

.channel-container {
}

.channel-item {
  transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.channel-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.channel-item img {
  transition: all 0.3s ease-in-out;
  backface-visibility: hidden;
}

.channel-item:hover img {
  transform: scale(1.05);
  box-shadow: 0 0 20px var(--overlay-light-10);
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
  filter: drop-shadow(var(--shadow-drop-sm));
}

@media (hover: none) {
  .settings-toggle {
    opacity: 1;
  }
}
  /* 刷新图标旋转 */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin-anim { animation: spin 0.8s linear infinite; }

  /* 刷新蒙层，保留旧卡片 DOM，降低突变感 */
  .channel-item.is-refreshing::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, var(--overlay-light-06), transparent);
    animation: shimmer 1.2s infinite;
    pointer-events: none;
    border-radius: inherit;
  }
  @keyframes shimmer { 0% { transform: translateX(-100%);} 100% { transform: translateX(100%);} }

  .avatar-sheen {
    background: linear-gradient(to bottom, transparent, var(--bg-tertiary));
  }
</style>

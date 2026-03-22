<template>
  <div class="subscribed-page flex flex-col h-full bg-background text-foreground">
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
          variant="secondary"
          size="xs"
          class="ml-2 whitespace-nowrap rounded-full"
          @click="showAddDialog = true"
        >
          <PlusIcon class="h-4 w-4" />
          <span>添加订阅</span>
        </Button>
        <Button
          variant="destructive"
          size="xs"
          class="ml-2 whitespace-nowrap rounded-full"
          @click="showImportDialog = true"
        >
          <ArrowDownTrayIcon class="h-4 w-4" />
          <span>导入订阅</span>
        </Button>

      </FeedToolbar>
    </div>

    <div
      ref="scrollContainer"
      class="channel-container scrollbar-hide pt-0 flex-grow overflow-y-auto"
      @scroll="handleScrollPosition"
    >
      <div class="content-container" v-if="loadError">
        <Alert variant="destructive" class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <AlertTitle>加载失败</AlertTitle>
            <AlertDescription class="break-words">
              {{ `加载失败：${loadError?.message || loadError}` }}
            </AlertDescription>
          </div>
          <Button variant="secondary" size="sm" class="rounded-full" @click="refreshList">重试</Button>
        </Alert>
      </div>
      <div class="content-container">
        <!-- 频道列表 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
          <div v-for="subscription in subscriptions" :key="subscription.id"
               class="channel-item relative group cursor-pointer"

               :class="{ 'is-refreshing': isResetting }"
               @click="getSubscriptionVideos(subscription.id)"
          >
            <div class="channel-item__media">
              <div class="channel-item__halo"></div>
              <div class="relative w-16 h-16">
                <img
                  :alt="subscription.name"
                  :src="getAvatarSrc(subscription.avatar, subscription.id)"
                  class="w-full h-full rounded-[1.25rem] object-cover ring-1 ring-border transition-transform duration-300 group-hover:scale-105"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, subscription.id)"
                />
                <div class="absolute -inset-1 avatar-sheen opacity-30 rounded-[1.5rem]"></div>
              </div>
            </div>

            <div class="channel-item__body">
              <div class="channel-item__header">
                <div class="min-w-0">
                  <h3 class="channel-item__title">{{ subscription.name }}</h3>
                  <p class="channel-item__meta">订阅于 {{ formatDate(subscription.created_at) }}</p>
                </div>
                <span v-if="subscription.type === 'PLAYLIST'" 
                      class="channel-item__badge"
                      title="播放列表">
                  播放列表
                </span>
              </div>

              <div class="channel-item__stats">
                <div class="channel-item__stat">
                  <span class="channel-item__stat-label">总视频</span>
                  <span class="channel-item__stat-value">{{ subscription.total_videos }}</span>
                </div>
                <div class="channel-item__stat">
                  <span class="channel-item__stat-label">已解析</span>
                  <span class="channel-item__stat-value">{{ subscription.total_extract }}</span>
                </div>
              </div>
            </div>

            <button class="settings-toggle absolute top-3 right-3 p-2 bg-card/88 border border-border rounded-full hover:bg-accent transition-colors duration-200 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100"
                    @click.stop="openSettings(subscription)">
              <svg class="h-3.5 w-3.5 text-foreground" fill="currentColor" viewBox="0 0 20 20"
                   xmlns="http://www.w3.org/2000/svg">
                <path clip-rule="evenodd"
                      d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                      fill-rule="evenodd"/>
              </svg>
            </button>

            <!-- YouTube风格的更新状态指示器 -->
            <div v-if="getRefreshState(subscription.id).isRefreshing"
                 class="absolute top-3 left-3 bg-card/92 border border-border text-foreground/80 text-2xs px-2 py-1 rounded-full shadow-sm">
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
            <div class="w-2 h-2 bg-destructive rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-destructive rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-destructive rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
          </div>
        </div>

        <!-- 全部加载完毕 -->
        <div v-if="allLoaded" class="mt-4 mb-4 text-center text-muted-foreground">
          <p>已经到底啦</p>
        </div>
      </div>
    </div>

    <!-- 设置模态框 -->
    <div v-if="showSettings" class="fixed inset-0 bg-overlay flex items-center justify-center z-50 backdrop-blur-sm"
         @click.self="closeSettings">
      <div class="bg-card border border-border rounded-[1.5rem] p-6 w-full max-w-md shadow-xl">
        <h2 class="text-xl font-bold mb-4 text-foreground">{{ selectedSubscription.name }} 设置</h2>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <span class="text-foreground">标记为敏感内容</span>
            <Switch
              :checked="!!selectedSubscription.is_nsfw"
              @update:checked="(value) => { selectedSubscription.is_nsfw = !!value; updateNsfwStatus(!!value) }"
            />
          </div>

          <!-- 手动更新按钮 -->
          <div class="space-y-3">
            <button
              class="w-full py-2 bg-secondary text-foreground rounded-xl hover:bg-accent disabled:bg-card disabled:cursor-not-allowed transition-colors duration-200 text-sm"
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
              <p class="text-destructive mb-2">{{ getRefreshState(selectedSubscription.id).lastError || '更新失败' }}</p>
              <button
                class="w-full py-1.5 bg-secondary text-foreground rounded-xl hover:bg-accent transition-colors duration-200"
                @click="handleRetryRefresh(selectedSubscription.id)"
              >
                重试更新
              </button>
            </div>
          </div>

          <button
            :disabled="getRefreshState(selectedSubscription.id).isRefreshing"
            :class="[
              'w-full py-2 text-foreground rounded-lg transition-colors duration-200 text-sm',
              getRefreshState(selectedSubscription.id).isRefreshing
                ? 'bg-card cursor-not-allowed'
                : 'bg-destructive hover:bg-destructive/90'
            ]"
            @click="unsubscribe(selectedSubscription.id)"
          >
            取消订阅
          </button>
          <p v-if="unsubscribeError" class="mt-2 text-xs text-destructive">{{ unsubscribeError }}</p>
        </div>
        <button class="mt-6 w-full py-2 bg-secondary text-foreground rounded-xl hover:bg-accent transition-colors duration-200 text-sm font-medium"
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
import FeedToolbar from '@/components/feed/FeedToolbar.vue';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { PlusIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline';        
import {useRouter} from "vue-router";
import { useRefreshTriggers } from '../composables/useRefreshTriggers';
import AddChannelDialog from '@/components/dialogs/AddChannelDialog.vue';
import ImportSubscriptionDialog from '@/components/dialogs/ImportSubscriptionDialog.vue';

import {formatDate} from '../utils/dateFormat';
import {useScrollPosition} from '../composables/useScrollPosition';
import {useSubscriptionRefresh} from '../composables/useSubscriptionRefresh';
import { useFeedFilters } from '../composables/useFeedFilters';
import { useImageFallback } from '../composables/useImageFallback';
import {
  getSubscriptions as apiGetSubscriptions,
  unsubscribe as apiUnsubscribe,
  updateNsfwStatus as apiUpdateNsfwStatus,
} from '@/api'

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

  const { data, error } = await apiGetSubscriptions({
    query: searchQuery.value,
    nsfw: nsfw.value,
    site: site.value,
    page: currentPage.value,
    page_size: 100
  });

  if (!error) {
    const newSubscriptions = Array.isArray(data?.data) ? data.data : (Array.isArray(data) ? data : []);
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
  } else {
    loadError.value = error || '获取订阅列表失败';
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

  const { error } = await apiUnsubscribe(subscriptionId);

  if (!error) {
    subscriptions.value = subscriptions.value.filter(subscription => subscription.id !== subscriptionId);
    closeSettings();
  } else {
    unsubscribeError.value = error?.message || '取消订阅失败';
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
  const { error } = await apiUpdateNsfwStatus(selectedSubscription.value.id, isNsfw);

  if (!error) {
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
  overflow: hidden;
  border-radius: 1.5rem;
  border: 1px solid hsl(var(--border) / 0.78);
  background:
    linear-gradient(180deg, hsl(var(--card)), color-mix(in srgb, hsl(var(--card)) 72%, hsl(var(--secondary))));
  box-shadow: 0 16px 36px hsl(var(--surface-shadow));
}

.channel-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 24px 48px hsl(var(--surface-shadow));
}

.channel-item img {
  transition: all 0.3s ease-in-out;
  backface-visibility: hidden;
}

.channel-item:hover img {
  transform: scale(1.05);
  box-shadow: 0 22px 30px hsl(var(--surface-shadow));
}

.channel-item__media {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 8.5rem;
  padding: 1.35rem 1rem 0.75rem;
  background:
    radial-gradient(circle at top, hsl(var(--primary) / 0.14), transparent 58%),
    linear-gradient(180deg, hsl(var(--background) / 0.34), transparent);
}

.channel-item__halo {
  position: absolute;
  inset: 1.15rem 1rem auto;
  height: 4.4rem;
  border-radius: 1.4rem;
  background: linear-gradient(135deg, hsl(var(--primary) / 0.16), transparent 70%);
  opacity: 0.8;
}

.channel-item__body {
  flex: 1;
  display: grid;
  gap: 1rem;
  padding: 0.2rem 1rem 1rem;
}

.channel-item__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.6rem;
}

.channel-item__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.95rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.channel-item__meta {
  margin-top: 0.28rem;
  font-size: 0.72rem;
  color: hsl(var(--muted-foreground));
}

.channel-item__badge {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0.28rem 0.55rem;
  border-radius: 9999px;
  background: hsl(var(--info) / 0.12);
  color: hsl(var(--info));
  font-size: 0.67rem;
  font-weight: 600;
}

.channel-item__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.channel-item__stat {
  display: grid;
  gap: 0.16rem;
  padding: 0.7rem 0.78rem;
  border-radius: 1rem;
  background: hsl(var(--background) / 0.58);
  border: 1px solid hsl(var(--border) / 0.68);
}

.channel-item__stat-label {
  font-size: 0.68rem;
  color: hsl(var(--muted-foreground));
}

.channel-item__stat-value {
  font-size: 0.92rem;
  font-weight: 600;
  color: hsl(var(--foreground));
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
    background: linear-gradient(180deg, transparent, hsl(var(--primary) / 0.2));
  }
</style>

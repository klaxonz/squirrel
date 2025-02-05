<template>
  <div class="subscribed-page flex flex-col h-full bg-[#0f0f0f] text-white">
    <div class="flex items-center pt-4 px-4">
      <SearchBar ref="searchBar" class="flex-grow" @search="handleSearch"/>
      <button 
        class="ml-4 h-9 px-6 min-w-[120px] bg-white/10 hover:bg-white/15 text-white rounded-full flex items-center justify-center transition-colors whitespace-nowrap"
        @click="showAddDialog = true"
      >
        <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
          <path clip-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" fill-rule="evenodd" />
        </svg>
        <span class="ml-2 text-sm font-medium">添加订阅</span>
      </button>
    </div>

    <div class="channel-container pt-4 flex-grow overflow-y-auto">
      <div class="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8">
        <!-- 频道列表 -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-3">
          <div v-for="subscription in subscriptions" :key="subscription.id"
               class="channel-item bg-[#202020] rounded-lg overflow-hidden hover:bg-[#303030] transition-all duration-200 relative group"
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
          <template v-if="selectedSubscription.is_enable">
            <div class="flex items-center justify-between">
              <span class="text-sm text-[#fff]">自动下载视频</span>
              <ToggleSwitch v-model="selectedSubscription.is_auto_download"
                            @update:modelValue="(value) => toggleAutoDownload(selectedSubscription.id, value)"/>
            </div>
            <div v-if="selectedSubscription.is_auto_download" class="flex items-center justify-between">
              <span class="text-sm text-[#fff]">下载全部视频</span>
              <ToggleSwitch v-model="selectedSubscription.is_download_all"
                            @update:modelValue="(value) => toggleDownloadAll(selectedSubscription.id, value)"/>
            </div>
          </template>
          <button class="w-full py-2 bg-[#cc0000] text-white rounded-lg hover:bg-[#990000] transition-colors duration-200 text-sm"
                  @click="unsubscribe(selectedSubscription.id)">
            取消订阅
          </button>
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

    <!-- Toast 提示 -->
    <Toast 
      v-if="toast.show"
      :duration="3000"
      :message="toast.message"
      :type="toast.type"
    />
  </div>
</template>

<script setup>
import {nextTick, onMounted, onUnmounted, ref, watch} from 'vue';
import axios from '../utils/axios';
import SearchBar from '../components/SearchBar.vue';
import ToggleSwitch from '../components/ToggleSwitch.vue';
import {useRouter} from "vue-router";
import useCustomToast from '../composables/useToast';
import AddChannelDialog from '../components/AddChannelDialog.vue';
import Toast from '../components/Toast.vue';
import {formatDate} from '../utils/dateFormat';

const router = useRouter();

const subscriptions = ref([]);
const loading = ref(false);
const allLoaded = ref(false);
const currentPage = ref(1);
const searchQuery = ref('');
const searchBar = ref(null);

const showSettings = ref(false);
const selectedSubscription = ref(null);

const observer = ref(null);
const loadingTrigger = ref(null);

const { displayToast, confirm } = useCustomToast();

const showAddDialog = ref(false);
const toast = ref({
  show: false,
  message: '',
  type: 'success'
});

const setupIntersectionObserver = () => {
  observer.value = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loading.value && !allLoaded.value) {
          loadMore();
        }
      },
      {
        root: document.querySelector('.channel-container'),
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
  try {
    const response = await axios.get('/api/subscription/list', {
      params: {
        query: searchQuery.value,
        page: currentPage.value,
        page_size: 100
      }
    });
    if (response.data.code === 0) {
      const newSubscriptions = response.data.data.data;
      subscriptions.value = [...subscriptions.value, ...newSubscriptions.map(subscription => ({
        ...subscription,
        total_videos: subscription.total_videos || 0,
        total_extract: subscription.total_extract || 0
      }))];
      currentPage.value++;
      if (newSubscriptions.length < 20) {
        allLoaded.value = true;
      }

      nextTick(() => {
        if (loadingTrigger.value && observer.value) {
          observer.value.observe(loadingTrigger.value);
        }
      });
    }
  } catch (error) {
    console.error('获取频道列表失败:', error);
  } finally {
    loading.value = false;
  }
};

const handleSearch = (query) => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value);
  }
  searchQuery.value = query;
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadSubscriptions();
};

const loadMore = () => {
  loadSubscriptions();
};

const openSettings = (subscription) => {
  selectedSubscription.value = {...subscription};
  showSettings.value = true;
};

const closeSettings = () => {
  showSettings.value = false;
  selectedSubscription.value = null;
};

const toggleAutoDownload = async (subscriptionId, status) => {
  try {
    await axios.post('/api/subscription/toggle-auto-download', {subscription_id: subscriptionId, is_enable: status});
    updateLocalSubscription(subscriptionId, {is_auto_download: status});
    if (!status) {
      // 如果关闭自动下载，同时关闭下载全部视频
      await toggleDownloadAll(subscriptionId, false);
    }
  } catch (error) {
    console.error('更新自动下载状态失败:', error);
  }
};

const toggleDownloadAll = async (subscriptionId, status) => {
  try {
    await axios.post('/api/subscription/toggle-download-all', {subscription_id: subscriptionId, is_enable: status});
    updateLocalSubscription(subscriptionId, {is_download_all: status});
  } catch (error) {
    console.error('更新下载全部状态失败:', error);
  }
};

const updateLocalSubscription = (subscriptionId, updates) => {
  const index = subscriptions.value.findIndex(c => c.id === subscriptionId);
  if (index !== -1) {
    subscriptions.value[index] = {...subscriptions.value[index], ...updates};
  }
  if (selectedSubscription.value && selectedSubscription.value.id === subscriptionId) {
    selectedSubscription.value = {...selectedSubscription.value, ...updates};
  }
};

const unsubscribe = async (subscriptionId) => {
  const confirmed = await confirm('确定要取消订阅这个频道吗？这将删除所有相关的视频记录。');
  
  if (confirmed) {
    try {
      const response = await axios.post('/api/subscription/unsubscribe', {subscription_id: subscriptionId});
      if (response.data.code === 0) {
        subscriptions.value = subscriptions.value.filter(subscription => subscription.id !== subscriptionId);
        displayToast('频道已成功取消订阅');
        closeSettings();
      } else {
        throw new Error(response.data.msg || '取消订阅失败');
      }
    } catch (error) {
      console.error('取消订阅失败:', error);
      displayToast(error.message || '取消订阅失败', { type: 'error' });
    }
  }
};

const getSubscriptionVideos = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`);
}

const showToast = (message, type = 'success') => {
  toast.value = {
    show: true,
    message,
    type
  };
  
  // 3秒后隐藏
  setTimeout(() => {
    toast.value.show = false;
  }, 3000);
};

const handleImageError = (event) => {
  event.target.src = '/squirrel-icon.svg';
};

const handleChannelAdded = () => {
  showToast('频道添加成功');
  subscriptions.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadSubscriptions();
};

onMounted(() => {
  loadSubscriptions();
  nextTick(() => {
    setupIntersectionObserver();
  });
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
</style>

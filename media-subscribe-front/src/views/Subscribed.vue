<template>
  <div class="subscribed-page flex flex-col h-full bg-[#0f0f0f] text-white">
    <SearchBar class="pt-4 px-4" @search="handleSearch" ref="searchBar" />
    
    <div class="channel-container pt-4 flex-grow overflow-y-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- 频道列表 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          <div v-for="channel in channels" :key="channel.id" class="channel-item bg-[#202020] rounded-lg overflow-hidden hover:bg-[#303030] transition-all duration-200 relative group">
            <router-link :to="{ name: 'ChannelDetail', params: { id: channel.channel_id } }">
              <img :src="channel.avatar" :alt="channel.name" class="w-full h-32 object-cover" />
              <div class="p-4">
                <h3 class="text-sm font-semibold truncate text-white">{{ channel.name }}</h3>
                <p class="text-xs text-[#aaa] mt-1">
                  总视频: {{ channel.total_videos }} | 已解析: {{ channel.total_extract }}
                </p>
                <p class="text-xs text-[#aaa] mt-1">订阅时间: {{ formatDate(channel.created_at) }}</p>
              </div>
            </router-link>
            <button @click.stop="openSettings(channel)" class="absolute top-2 right-2 p-2 bg-black bg-opacity-50 rounded-full hover:bg-opacity-75 transition-colors duration-200 opacity-0 group-hover:opacity-100">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 加载更多按钮 -->
        <div v-if="!allLoaded && !loading" class="mt-8 mb-8 text-center">
          <button @click="loadMore" class="px-6 py-2 bg-[#cc0000] text-white font-medium rounded-full hover:bg-[#990000] transition-colors duration-200">
            加载更多
          </button>
        </div>

        <!-- 加载中状态 -->
        <div v-if="loading" class="mt-8 mb-8 text-center">
          <p class="text-[#aaa]">加载中...</p>
        </div>

        <!-- 全部加载完毕 -->
        <div v-if="allLoaded" class="mt-8 mb-8 text-center text-[#aaa]">
          <p>已经到底啦</p>
        </div>
      </div>
    </div>

    <!-- 设置模态框 -->
    <div v-if="showSettings" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="closeSettings">
      <div class="bg-[#212121] rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4 text-white">{{ selectedChannel.name }} 设置</h2>
        <div class="space-y-6">
          <div class="flex items-center justify-between">
            <span class="text-sm text-[#fff]">开启监控</span>
            <ToggleSwitch v-model="selectedChannel.if_enable" @update:modelValue="(value) => toggleStatus(selectedChannel.id, value)" />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-[#fff]">解析全部视频</span>
            <ToggleSwitch v-model="selectedChannel.if_extract_all" @update:modelValue="(value) => toggleExtractAll(selectedChannel.id, value)" />
          </div>
          <template v-if="selectedChannel.if_enable">
            <div class="flex items-center justify-between">
              <span class="text-sm text-[#fff]">自动下载视频</span>
              <ToggleSwitch v-model="selectedChannel.if_auto_download" @update:modelValue="(value) => toggleAutoDownload(selectedChannel.id, value)" />
            </div>
            <div v-if="selectedChannel.if_auto_download" class="flex items-center justify-between">
              <span class="text-sm text-[#fff]">下载全部视频</span>
              <ToggleSwitch v-model="selectedChannel.if_download_all" @update:modelValue="(value) => toggleDownloadAll(selectedChannel.id, value)" />
            </div>
          </template>
          <button @click="unsubscribeChannel(selectedChannel.id)" class="w-full py-2 bg-[#cc0000] text-white rounded-lg hover:bg-[#990000] transition-colors duration-200 text-sm">
            取消订阅
          </button>
        </div>
        <button @click="closeSettings" class="mt-6 w-full py-2 bg-[#606060] text-white rounded-lg hover:bg-[#808080] transition-colors duration-200 text-sm font-medium">
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '../utils/axios';
import SearchBar from '../components/SearchBar.vue';
import ToggleSwitch from '../components/ToggleSwitch.vue';

const channels = ref([]);
const loading = ref(false);
const allLoaded = ref(false);
const currentPage = ref(1);
const searchQuery = ref('');
const searchBar = ref(null);

const showSettings = ref(false);
const selectedChannel = ref(null);

const loadChannels = async () => {
  if (loading.value || allLoaded.value) return;
  
  loading.value = true;
  try {
    const response = await axios.get('/api/channel/list', {
      params: {
        query: searchQuery.value,
        page: currentPage.value,
        pageSize: 20
      }
    });
    if (response.data.code === 0) {
      const newChannels = response.data.data.data;
      channels.value = [...channels.value, ...newChannels.map(channel => ({
        ...channel,
        total_videos: channel.total_videos || 0,
        total_extract: channel.total_extract || 0
      }))];
      currentPage.value++;
      if (newChannels.length < 20) {
        allLoaded.value = true;
      }
    }
  } catch (error) {
    console.error('获取频道列表失败:', error);
  } finally {
    loading.value = false;
  }
};

const handleSearch = (query) => {
  searchQuery.value = query;
  channels.value = [];
  currentPage.value = 1;
  allLoaded.value = false;
  loadChannels();
};

const loadMore = () => {
  loadChannels();
};

const openSettings = (channel) => {
  selectedChannel.value = { ...channel };
  showSettings.value = true;
};

const closeSettings = () => {
  showSettings.value = false;
  selectedChannel.value = null;
};

const toggleStatus = async (channelId, status) => {
  try {
    console.log(`Updating status for channel ${channelId} to ${status}`);
    await axios.post('/api/channel/toggle-status', { channel_id: channelId, if_enable: status });
    updateLocalChannel(channelId, { if_enable: status });
    if (!status) {
      // 如果关闭监控，同时关闭其他选项
      await toggleAutoDownload(channelId, false);
      await toggleExtractAll(channelId, false);
      await toggleDownloadAll(channelId, false);
    }
  } catch (error) {
    console.error('更新频道状态失败:', error);
  }
};

const toggleAutoDownload = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-auto-download', { channel_id: channelId, if_enable: status });
    updateLocalChannel(channelId, { if_auto_download: status });
    if (!status) {
      // 如果关闭自动下载，同时关闭下载全部视频
      await toggleDownloadAll(channelId, false);
    }
  } catch (error) {
    console.error('更新自动下载状态失败:', error);
  }
};

const toggleDownloadAll = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-download-all', { channel_id: channelId, if_enable: status });
    updateLocalChannel(channelId, { if_download_all: status });
  } catch (error) {
    console.error('更新下载全部状态失败:', error);
  }
};

const toggleExtractAll = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-extract-all', { channel_id: channelId, if_enable: status });
    updateLocalChannel(channelId, { if_extract_all: status });
  } catch (error) {
    console.error('更新提取全部状态失败:', error);
  }
};

const updateLocalChannel = (channelId, updates) => {
  const index = channels.value.findIndex(c => c.id === channelId);
  if (index !== -1) {
    channels.value[index] = { ...channels.value[index], ...updates };
  }
  if (selectedChannel.value && selectedChannel.value.id === channelId) {
    selectedChannel.value = { ...selectedChannel.value, ...updates };
  }
};

const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
};

const unsubscribeChannel = async (channelId) => {
  if (confirm('确定要取消订阅这个频道吗？这将删除所有相关的视频记录。')) {
    try {
      const response = await axios.post('/api/channel/unsubscribe', { id: channelId });
      if (response.data.code === 0) {
        channels.value = channels.value.filter(channel => channel.id !== channelId);
        showToast('频道已成功取消订阅', false);
        closeSettings();
      } else {
        throw new Error(response.data.msg || '取消订阅失败');
      }
    } catch (error) {
      console.error('取消订阅失败:', error);
      showToast(error.message || '取消订阅失败', true);
    }
  }
};

const showToast = (message, isError = false) => {
  // 实现一个简单的 toast 通知
  alert(message); // 这里可以替换为更优雅的 toast 实现
};

onMounted(() => {
  loadChannels();
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
}

.channel-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}
</style>

<template>
  <div class="subscribed-channels bg-gray-100 min-h-screen  sm:p-6">
    <div class="max-w-6xl mx-auto">

      <!-- 搜索栏 -->
      <div class="search-bar sticky top-0 bg-white z-10 p-4 shadow-sm">
        <div class="flex items-center max-w-3xl mx-auto relative">
          <input 
            v-model="searchQuery" 
            @keyup.enter="handleSearchClick"
            type="text" 
            placeholder="搜索频道..." 
            class="flex-grow h-8 px-4 pr-10 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200"
          >
          <button 
            v-if="searchQuery"
            @click="clearSearch"
            class="absolute right-20 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </button>
          <button 
            @click="handleSearchClick"
            class="h-8 px-6 text-sm font-medium bg-blue-500 text-white rounded-r-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-50 focus:ring-offset-2 transition duration-200"
          >
            搜索
          </button>
        </div>
      </div>

      <!-- 频道列表 -->
      <div v-if="channels.length > 0" class="space-y-2 px-4">
        <div v-for="channel in channels" :key="channel.id" class="bg-white sm:p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300">
          <div class="flex flex-col  px-4 pt-4 sm:flex-row items-start sm:items-center justify-between">
            <div class="flex items-center mb-4 sm:mb-0">
              <img :src="channel.avatar" :alt="channel.name" referrerpolicy="no-referrer" class="w-12 h-12 sm:w-16 sm:h-16 rounded-full object-cover mr-4" />
              <div>
                <div class="flex items-center">
                  <h2 class="text-lg sm:text-xl font-semibold text-gray-800">{{ channel.name }}</h2>
              
                </div>
                <div class="flex flex-wrap gap-2 mt-2 text-xs sm:text-sm text-gray-600">
                  <a :href="channel.url" target="_blank" rel="noopener noreferrer" class="text-blue-500 hover:text-blue-600">
                    查看频道
                  </a>
                  <span>总视频: {{ channel.total_videos }}</span>
                  <span>已提取: {{ channel.total_extract }}</span>
                </div>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 w-full sm:w-auto mt-2 sm:mt-0">
              <ToggleLabel 
                v-model="channel.if_enable" 
                @update:modelValue="toggleStatus(channel.id, $event)" 
                label="启用" 
              />
              <ToggleLabel 
                v-model="channel.if_auto_download" 
                @update:modelValue="toggleAutoDownload(channel.id, $event)" 
                label="自动下载" 
                :enabled="channel.if_enable"
              />
              <ToggleLabel 
                v-if="channel.if_auto_download"
                v-model="channel.if_download_all" 
                @update:modelValue="toggleDownloadAll(channel.id, $event)" 
                label="下载全部" 
                :enabled="channel.if_enable && channel.if_auto_download"
              />
              <ToggleLabel 
                v-model="channel.if_extract_all" 
                @update:modelValue="toggleExtractAll(channel.id, $event)" 
                label="提取全部" 
                :enabled="channel.if_enable"
              />
            </div>
        
          </div>
          <div class="mt-2 px-4 py-1 bg-gray-100 rounded-b-lg text-xs font-medium">
              <span>订阅时间: {{ channel.created_at }}</span>
            </div>
        </div>
      </div>

      <!-- 加载中状态 -->
      <div v-if="loading" class="text-center py-4">
        <p>加载中...</p>
      </div>

      <!-- 错误状态 -->
      <div v-if="error" class="text-center text-red-500 py-4">
        <p>{{ error }}</p>
      </div>

      <!-- 无限滚动 -->
      <infinite-loading @infinite="infiniteHandler">
        <template #no-more>
          <p class="text-center text-gray-500 my-4 sm:my-6">没有更多频道了</p>
        </template>
        <template #no-results>
          <p class="text-center text-gray-500 my-4 sm:my-6">没有找到匹配的频道</p>
        </template>
        <template #error>
          <p class="text-center text-red-500 my-4 sm:my-6">加载失败，请重试</p>
        </template>
      </infinite-loading>
    </div>
  </div>
</template>

<script setup>
import axios from '../utils/axios';
import { ref, onMounted } from 'vue';
import { debounce } from 'lodash';
import InfiniteLoading from 'v3-infinite-loading';
import ToggleLabel from '../components/ToggleLabel.vue';

const channels = ref([]);
const currentPage = ref(1);
const searchQuery = ref('');
const loading = ref(false);
const error = ref(null);

const infiniteHandler = async ($state) => {
  if (loading.value) return;
  loading.value = true;
  try {
    const response = await axios.get('/api/channel/list', {
      params: {
        query: searchQuery.value,
        page: currentPage.value,
        pageSize: 10
      }
    });
    if (response.data.code === 0) {
      const newChannels = response.data.data.data;
      if (newChannels.length) {
        channels.value.push(...newChannels);
        currentPage.value++;
        $state.loaded();
      } else {
        $state.complete();
      }
    } else {
      throw new Error(response.data.msg || '获取频道列表失败');
    }
  } catch (err) {
    console.error('获取频道列表失败:', err);
    error.value = err.message || '获取频道列表失败';
    $state.error();
  } finally {
    loading.value = false;
  }
};

const handleSearchClick = () => {
  channels.value = [];
  currentPage.value = 1;
  error.value = null;
  infiniteHandler({ loaded: () => {}, complete: () => {}, error: () => {} });
};

const clearSearch = () => {
  searchQuery.value = '';
  handleSearchClick();
};

const toggleStatus = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-status', { channel_id: channelId, if_enable: status });
  } catch (error) {
    console.error('更新频道状态失败:', error);
  }
};

const toggleAutoDownload = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-auto-download', { channel_id: channelId, if_enable: status });
    if (!status) {
      const channel = channels.value.find(c => c.id === channelId);
      if (channel) {
        channel.if_download_all = false;
        await toggleDownloadAll(channelId, false);
      }
    }
  } catch (error) {
    console.error('更新自动下载状态失败:', error);
  }
};

const toggleDownloadAll = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-download-all', { channel_id: channelId, if_enable: status });
  } catch (error) {
    console.error('更新下载全部状态失败:', error);
  }
};

const toggleExtractAll = async (channelId, status) => {
  try {
    await axios.post('/api/channel/toggle-extract-all', { channel_id: channelId, if_enable: status });
  } catch (error) {
    console.error('更新提取全部状态失败:', error);
  }
};

onMounted(() => {
  infiniteHandler({ loaded: () => {}, complete: () => {}, error: () => {} });
});
</script>

<style scoped>
.subscribed-channels {
  max-width: 800px;
  margin: 0 auto;
}

.form-checkbox {
  @apply rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50;
}

.search-bar {
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 10;
  padding: 1rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.search-bar input {
  border-right: none;
}

.search-bar button {
  border-left: none;
}

.search-bar input:focus,
.search-bar button:focus {
  box-shadow: 0 0 0 0 rgba(111, 164, 248, 0.5);
}
</style>
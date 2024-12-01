<template>
  <div v-if="show" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
    <div class="bg-[#1f1f1f] rounded-lg w-full max-w-lg mx-4">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-[#272727]">
        <h3 class="text-lg font-medium">添加播客</h3>
        <button @click="$emit('close')" class="text-[#aaaaaa] hover:text-white">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 表单内容 -->
      <div class="p-6">
        <div class="space-y-4">
          <!-- RSS URL输入 -->
          <div>
            <label class="block text-sm font-medium text-[#aaaaaa] mb-1">RSS 订阅地址</label>
            <input 
              v-model="rssUrl"
              type="url"
              placeholder="请输入播客的 RSS 地址"
              class="w-full px-3 py-2 bg-[#272727] rounded border border-[#333] focus:border-[#cc0000] focus:outline-none text-white text-sm"
              :disabled="loading"
            >
          </div>

          <!-- 预览区域 -->
          <div v-if="previewData" class="bg-[#272727] rounded-lg p-4 mt-4">
            <div class="flex items-start space-x-4">
              <img 
                :src="previewData.cover_url" 
                :alt="previewData.title"
                class="w-20 h-20 rounded object-cover flex-shrink-0"
              >
              <div class="flex-grow min-w-0">
                <h4 class="font-medium text-sm line-clamp-2">{{ previewData.title }}</h4>
                <p class="text-xs text-[#aaaaaa] mt-1">{{ previewData.author }}</p>
                <p class="text-xs text-[#aaaaaa] mt-1 line-clamp-2">{{ previewData.description }}</p>
              </div>
            </div>
          </div>

          <!-- 错误提示 -->
          <p v-if="error" class="text-[#cc0000] text-sm">{{ error }}</p>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="px-6 py-4 border-t border-[#272727] flex justify-end space-x-4">
        <button 
          @click="$emit('close')"
          class="px-4 py-2 text-sm text-[#aaaaaa] hover:text-white transition-colors"
          :disabled="loading"
        >
          取消
        </button>
        <button 
          v-if="!previewData"
          @click="handlePreview"
          class="px-4 py-2 text-sm bg-[#cc0000] text-white rounded hover:bg-[#aa0000] transition-colors disabled:opacity-50"
          :disabled="!rssUrl || loading"
        >
          <span v-if="loading">解析中...</span>
          <span v-else>预览</span>
        </button>
        <button 
          v-else
          @click="handleSubmit"
          class="px-4 py-2 text-sm bg-[#cc0000] text-white rounded hover:bg-[#aa0000] transition-colors disabled:opacity-50"
          :disabled="loading"
        >
          <span v-if="loading">添加中...</span>
          <span v-else>确认添加</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from '../utils/axios';

const props = defineProps({
  show: Boolean
});

const emit = defineEmits(['close', 'added']);

const rssUrl = ref('');
const loading = ref(false);
const error = ref('');
const previewData = ref(null);

const handlePreview = async () => {
  if (!rssUrl.value) return;
  
  loading.value = true;
  error.value = '';
  
  try {
    const response = await axios.post('/api/podcasts/channels/subscribe', {
      rss_url: rssUrl.value
    });
    previewData.value = response.data.data;
  } catch (err) {
    error.value = err.response?.data?.message || '解析RSS失败，请检查地址是否正确';
  } finally {
    loading.value = false;
  }
};

const handleSubmit = async () => {
  loading.value = true;
  error.value = '';
  
  try {
    await axios.post('/api/podcasts/channels/subscribe', {
      rss_url: rssUrl.value
    });
    emit('added');
    emit('close');
  } catch (err) {
    error.value = err.response?.data?.message || '添加播客失败，请稍后重试';
  } finally {
    loading.value = false;
  }
};
</script> 
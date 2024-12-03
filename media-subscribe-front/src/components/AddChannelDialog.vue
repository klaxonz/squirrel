<template>
  <div v-if="show" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
    <div class="bg-[#1f1f1f] rounded-lg w-full max-w-lg mx-4">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-[#272727]">
        <h3 class="text-lg font-medium">添加频道</h3>
        <button @click="$emit('close')" class="text-[#aaaaaa] hover:text-white">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 表单内容 -->
      <div class="p-6">
        <div class="space-y-4">
          <!-- URL输入 -->
          <div>
            <label class="block text-sm font-medium text-[#aaaaaa] mb-1">频道地址</label>
            <input 
              v-model="channelUrl"
              type="url"
              placeholder="请输入频道地址"
              class="w-full px-3 py-2 bg-[#272727] rounded border border-[#333] focus:border-[#cc0000] focus:outline-none text-white text-sm"
              :disabled="loading"
            >
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
          @click="handleSubmit"
          class="px-4 py-2 text-sm bg-[#cc0000] text-white rounded hover:bg-[#aa0000] transition-colors disabled:opacity-50"
          :disabled="!channelUrl || loading"
        >
          <span v-if="loading">添加中...</span>
          <span v-else>确认添加</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import axios from '../utils/axios';

const props = defineProps({
  show: Boolean
});

const emit = defineEmits(['close', 'added']);

const channelUrl = ref('');
const loading = ref(false);
const error = ref('');

// 监听 show 属性的变化，当对话框关闭时重置表单
watch(() => props.show, (newVal) => {
  if (!newVal) {
    channelUrl.value = '';
    error.value = '';
  }
});

const handleSubmit = async () => {
  if (!channelUrl.value) return;
  
  loading.value = true;
  error.value = '';
  
  try {
    await axios.post('/api/channel/subscribe', {
      url: channelUrl.value
    });
    emit('added');
    emit('close');
  } catch (err) {
    error.value = err.response?.data?.msg || '添加频道失败，请检查地址是否正确';
  } finally {
    loading.value = false;
  }
};
</script> 
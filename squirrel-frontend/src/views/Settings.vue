<template>
  <div class="settings-container bg-[#0f0f0f] text-white min-h-screen p-4 md:p-8">
    <h1 class="text-2xl font-bold mb-6">设置</h1>
    
    <div class="settings-section mb-8">
      <h2 class="text-xl font-semibold mb-4">消费者配置</h2>
      
      <div class="setting-item" v-for="(value, key) in settings" :key="key">
        <div class="flex justify-between items-center mb-2">
          <label :for="key" class="text-sm font-medium">{{ getLabel(key) }}</label>
          <span class="text-sm font-medium text-gray-400">{{ settings[key] }}</span>
        </div>
        <input 
          type="range" 
          :id="key" 
          v-model="settings[key]" 
          :min="getMin(key)" 
          :max="getMax(key)" 
          step="1"
          class="w-full h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer"
        >
      </div>
    </div>
    
    <button @click="saveSettings" class="save-button bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
      保存设置
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '../utils/axios';
import { useToast } from 'vue-toastification';

const toast = useToast();

const settings = ref({
  downloadConsumers: 1,
  extractConsumers: 2,
  subscribeConsumers: 1
});

const getLabel = (key) => {
  const labels = {
    downloadConsumers: '下载线程数',
    extractConsumers: '视频更新线程数',
    subscribeConsumers: '频道订阅线程数'
  };
  return labels[key];
};

const getMin = (key) => key === 'subscribeConsumers' ? 1 : 1;
const getMax = (key) => key === 'subscribeConsumers' ? 5 : 10;

onMounted(async () => {
  try {
    const response = await axios.get('/api/settings');
    if (response.data.code === 0) {
      settings.value = response.data.data;
    }
  } catch (error) {
    console.error('获取设置失败:', error);
    toast.error('加载设置失败');
  }
});

const saveSettings = async () => {
  try {
    const response = await axios.post('/api/settings', settings.value);
    if (response.data.code === 0) {
      toast.success('设置保存成功');
    } else {
      throw new Error(response.data.msg || '保存设置失败');
    }
  } catch (error) {
    console.error('保存设置失败:', error);
    toast.error('保存设置失败: ' + (error.message || '未知错误'));
  }
};
</script>

<style scoped>
.settings-container {
  max-width: 800px;
  margin: 0 auto;
}

.setting-item {
  margin-bottom: 1.5rem;
}

input[type="range"] {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #4a4a4a;
  outline: none;
  opacity: 0.7;
  transition: opacity 0.2s;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ff0000;
  cursor: pointer;
}

input[type="range"]::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ff0000;
  cursor: pointer;
}

.save-button {
  transition: background-color 0.2s;
}

.save-button:hover {
  background-color: #cc0000;
}
</style>

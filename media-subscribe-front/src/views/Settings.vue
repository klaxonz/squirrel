<template>
  <div class="settings-container">
    
    <div class="settings-card">
      <h2 class="settings-subtitle">消费者配置</h2>
      
      <div class="setting-item" v-for="(value, key) in settings" :key="key">
        <label :for="key" class="setting-label">{{ getLabel(key) }}</label>
        <div class="slider-container">
          <input 
            type="range" 
            :id="key" 
            v-model="settings[key]" 
            :min="getMin(key)" 
            :max="getMax(key)" 
            step="1"
            class="slider"
          >
          <span class="slider-value">{{ settings[key] }}</span>
        </div>
      </div>
    </div>
    
    <button @click="saveSettings" class="save-button">
      <span class="save-icon">💾</span>
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
  min-height: calc(100vh - 56px); /* Subtract the height of the bottom nav bar */
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 2rem;
  background-color: #f8fafc;
}

@media (min-width: 768px) {
  .settings-container {
    min-height: 100vh; /* Full height for desktop */
    padding-left: 4rem; /* Account for the side nav bar */
  }
}

.settings-card {
  width: 100%;
  max-width: 600px;
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.settings-subtitle {
  font-size: 1.25rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 1rem;
}

.setting-item {
  margin-bottom: 1.5rem;
}

.setting-label {
  display: block;
  font-size: 1rem;
  font-weight: 500;
  color: #475569;
  margin-bottom: 0.5rem;
}

.slider-container {
  display: flex;
  align-items: center;
}

.slider {
  flex-grow: 1;
  -webkit-appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: #e2e8f0;
  outline: none;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.slider:hover {
  opacity: 1;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
}

.slider-value {
  min-width: 2rem;
  text-align: center;
  font-weight: 600;
  color: #3b82f6;
  margin-left: 1rem;
}

.save-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0.75rem;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.save-button:hover {
  background-color: #2563eb;
}

.save-icon {
  margin-right: 0.5rem;
  font-size: 1.25rem;
}
</style>
<template>
  <div class="settings-container bg-[#0f0f0f] text-white min-h-screen p-4 md:p-8">
    <h1 class="text-2xl font-bold mb-6">内容偏好设置</h1>
    
    <div class="settings-section mb-8">
      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">{{ getLabel('showNsfw') }}</h3>
          <p class="text-sm text-gray-400">显示可能包含成人内容的媒体</p>
        </div>
        <label class="switch">
          <input type="checkbox" v-model="settings.showNsfw">
          <span class="slider"></span>
        </label>
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
  showNsfw: false
});

const getLabel = (key) => {
  const labels = {
    showNsfw: '显示敏感内容'
  };
  return labels[key];
};

onMounted(async () => {
  try {
    const response = await axios.get('/api/users/me/config');
    if (response.data.code === 0) {
      settings.value = {
        ...settings.value,
        ...response.data.data
      };
    }
  } catch (error) {
    console.error('获取设置失败:', error);
    toast.error('加载设置失败');
  }
});

const saveSettings = async () => {
  try {
    const response = await axios.put('/api/users/me/config', {
      settings: settings.value,
      merge: false
    });
    
    if (response.data.code === 0) {
      toast.success('设置保存成功');
      settings.value = response.data.data;
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

.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #4a4a4a;
  transition: .4s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #ef4444;
}

input:checked + .slider:before {
  transform: translateX(24px);
}

.save-button {
  transition: background-color 0.2s;
}

.save-button:hover {
  background-color: #cc0000;
}
</style>

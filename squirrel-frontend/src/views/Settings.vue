<template>
  <div class="settings-container bg-[#0f0f0f] text-white min-h-screen p-4 md:p-8">
    <h1 class="text-2xl font-bold mb-6">设置</h1>

    <!-- 用户偏好设置 -->
    <div class="settings-section mb-8">
      <h2 class="text-lg font-semibold mb-4 text-gray-300">内容偏好</h2>
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
      <button @click="saveSettings" class="save-button bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded mt-4">
        保存用户设置
      </button>
    </div>

    <!-- 系统配置 -->
    <div class="settings-section mb-8">
      <h2 class="text-lg font-semibold mb-4 text-gray-300">系统配置</h2>
      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">启用调度器（Scheduler）</h3>
          <p class="text-sm text-gray-400">按计划任务周期性执行订阅同步、重试等任务</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="systemConfig?.enable_scheduler"
            :disabled="systemLoading || systemSaving"
            @change="onSystemToggle('enable_scheduler', $event.target.checked)"
          >
          <span class="slider"></span>
        </label>
      </div>

      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">启用 Worker（队列消费）</h3>
          <p class="text-sm text-gray-400">开启后启动 Dramatiq Worker 进行队列消费</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="systemConfig?.enable_worker"
            :disabled="systemLoading || systemSaving"
            @change="onSystemToggle('enable_worker', $event.target.checked)"
          >
          <span class="slider"></span>
        </label>
      </div>

      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">NSFW 视频封面模糊</h3>
          <p class="text-sm text-gray-400">自动模糊显示标记为 NSFW 的视频封面</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="systemConfig?.blur_nsfw_thumbnails"
            :disabled="systemLoading || systemSaving"
            @change="onSystemToggle('blur_nsfw_thumbnails', $event.target.checked)"
          >
          <span class="slider"></span>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '../utils/axios';
import { useToast } from 'vue-toastification';
import { useSystemConfig } from '../composables/useSystemConfig';

const toast = useToast();

// 用户设置
const settings = ref({
  showNsfw: false
});

// 系统配置
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig();
const systemSaving = ref(false);

const getLabel = (key) => {
  const labels = {
    showNsfw: '显示敏感内容'
  };
  return labels[key];
};

onMounted(async () => {
  // 加载用户设置
  try {
    const response = await axios.get('/api/users/me/config');
    if (response.data.code === 0) {
      settings.value = {
        ...settings.value,
        ...response.data.data
      };
    }
  } catch (error) {
    console.error('获取用户设置失败:', error);
  }

  // 加载系统配置
  try {
    await loadSystemConfig();
  } catch (error) {
    console.error('获取系统配置失败:', error);
  }
});

const saveSettings = async () => {
  try {
    const response = await axios.put('/api/users/me/config', {
      settings: settings.value,
      merge: false
    });

    if (response.data.code === 0) {
      toast.success('用户设置保存成功');
      settings.value = response.data.data;
    } else {
      throw new Error(response.data.msg || '保存用户设置失败');
    }
  } catch (error) {
    console.error('保存用户设置失败:', error);
    toast.error('保存用户设置失败: ' + (error.message || '未知错误'));
  }
};

const onSystemToggle = async (key, val) => {
  systemSaving.value = true;
  try {
    await updateSystemConfig({ [key]: val });
    // 系统配置是即时生效的，不需要成功提示
  } catch (e) {
    console.error('系统配置操作失败:', e);
    toast.error('系统配置操作失败');
  } finally {
    systemSaving.value = false;
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

<template>
  <div class="settings-container bg-[#0f0f0f] text-white min-h-screen p-4 md:p-8">
    <h1 class="text-2xl font-bold mb-6">设置</h1>

    <!-- NSFW 内容设置 -->
    <div class="settings-section mb-8">
      <h2 class="text-lg font-semibold mb-4 text-gray-300">内容设置</h2>
      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">显示敏感内容</h3>
          <p class="text-sm text-gray-400">显示可能包含成人内容的媒体</p>
        </div>
        <label class="switch">
          <input 
            type="checkbox" 
            v-model="settings.showNsfw"
            :disabled="userSaving"
            @change="onUserSettingChange"
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

    <!-- 播放设置 -->
    <div class="settings-section mb-8">
      <h2 class="text-lg font-semibold mb-4 text-gray-300">播放设置</h2>
      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">自动播放</h3>
          <p class="text-sm text-gray-400">打开视频页面时自动开始播放</p>
        </div>
        <label class="switch">
          <input 
            type="checkbox" 
            v-model="settings.autoplay"
            :disabled="userSaving"
            @change="onUserSettingChange"
          >
          <span class="slider"></span>
        </label>
      </div>

      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">自动播放下一个</h3>
          <p class="text-sm text-gray-400">当前视频播放完毕后自动播放下一个视频</p>
        </div>
        <label class="switch">
          <input 
            type="checkbox" 
            v-model="settings.autoplayNext"
            :disabled="userSaving"
            @change="onUserSettingChange"
          >
          <span class="slider"></span>
        </label>
      </div>

      <div class="setting-item flex justify-between items-center py-3 border-b border-gray-700">
        <div>
          <h3 class="font-medium">循环播放</h3>
          <p class="text-sm text-gray-400">视频播放完毕后自动重新播放</p>
        </div>
        <label class="switch">
          <input 
            type="checkbox" 
            v-model="settings.loop"
            :disabled="userSaving"
            @change="onUserSettingChange"
          >
          <span class="slider"></span>
        </label>
      </div>
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
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '../utils/axios';
import { useSystemConfig } from '../composables/useSystemConfig';

// 用户设置
const settings = ref({
  showNsfw: false,
  autoplay: true,
  autoplayNext: true,
  loop: false
});
const userSaving = ref(false);

// 系统配置
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig();
const systemSaving = ref(false);

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

const onUserSettingChange = async () => {
  userSaving.value = true;
  try {
    const response = await axios.put('/api/users/me/config', {
      settings: settings.value,
      merge: false
    });

    if (response.data.code === 0) {
      settings.value = response.data.data;
    } else {
      throw new Error(response.data.msg || '保存用户设置失败');
    }
  } catch (error) {
    console.error('保存用户设置失败:', error);
    // 恢复到之前的值
    const response = await axios.get('/api/users/me/config');
    if (response.data.code === 0) {
      settings.value = {
        ...settings.value,
        ...response.data.data
      };
    }
  } finally {
    userSaving.value = false;
  }
};

const onSystemToggle = async (key, val) => {
  systemSaving.value = true;
  try {
    await updateSystemConfig({ [key]: val });
  } catch (e) {
    console.error('系统配置操作失败:', e);
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

input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

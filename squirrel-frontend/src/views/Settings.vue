<template>
  <div class="settings-container bg-[#0f0f0f] text-white min-h-screen p-4 md:p-8">
    <h1 class="text-2xl font-bold mb-4">设置</h1>

    <!-- Tab 导航 -->
    <div class="flex flex-wrap gap-2 mb-6 text-sm">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="currentTab = tab.key"
        class="px-4 py-2 rounded-full border text-sm transition-colors"
        :class="currentTab === tab.key
          ? 'bg-white text-black border-white'
          : 'bg-transparent border-white/20 text-gray-300 hover:bg-white/10'"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- NSFW 内容设置 -->
    <div v-if="currentTab === 'content'" class="settings-section mb-8">
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
    <div v-if="currentTab === 'playback'" class="settings-section mb-8">
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
    <div v-if="currentTab === 'system'" class="settings-section mb-8">
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

    <!-- 站点配置 -->
    <SiteConfigSection v-if="currentTab === 'sites'" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useSystemConfig } from '../composables/useSystemConfig';
import { useUserSettings } from '../composables/useUserSettings';
import SiteConfigSection from '../components/SiteConfigSection.vue';

// Tabs 配置
const tabs = [
  { key: 'content', label: '内容设置' },
  { key: 'playback', label: '播放设置' },
  { key: 'system', label: '系统配置' },
  { key: 'sites', label: '站点配置' },
];
const currentTab = ref('content');

// 用户设置
const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings();

// 系统配置
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig();
const systemSaving = ref(false);

onMounted(async () => {
  // 加载用户设置
  await loadUserSettings();

  // 加载系统配置
  try {
    await loadSystemConfig();
  } catch (error) {
    console.error('获取系统配置失败:', error);
  }

});

const onUserSettingChange = async () => {
  await saveUserSettings();
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

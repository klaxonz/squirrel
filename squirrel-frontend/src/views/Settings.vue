<template>
  <div class="settings-page bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-6 pb-6">
      <div class="settings-hero">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 class="text-2xl font-semibold text-foreground">设置</h1>
            <p class="text-sm text-muted-foreground mt-1">管理内容偏好、播放体验与系统服务。</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground/70">
            <div class="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-full">
              <span class="h-2 w-2 rounded-full" :class="statusDotClass"></span>
              <span>{{ statusLabel }}</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-full">
              <span class="text-muted-foreground/70">系统配置</span>
              <span class="text-foreground">{{ systemStatusLabel }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      class="content-container pb-10 flex-1 min-h-0 overflow-hidden"
    >
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-0 min-h-0 h-full">
        <aside class="lg:col-span-3 lg:sticky lg:top-0 self-start">

          <div class="settings-nav bg-card/40 border border-border rounded-2xl p-2 lg:rounded-r-none lg:border-r-0">
            <div class="flex lg:flex-col gap-2 overflow-x-auto scrollbar-hide">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                @click="currentTab = tab.key"
                class="tab-button group relative text-left min-w-[11rem] flex-1 lg:flex-none px-4 py-3 rounded-xl border transition-colors"
                :class="currentTab === tab.key
                  ? 'bg-muted border-border text-foreground shadow-sm'
                  : 'bg-transparent border-border text-muted-foreground hover:bg-card/60'"
                :aria-current="currentTab === tab.key ? 'page' : undefined"
              >
                <span
                  class="tab-accent absolute left-3 top-3 bottom-3 w-0.5 rounded-full transition-opacity"
                  :class="currentTab === tab.key ? 'opacity-100 bg-destructive' : 'opacity-0 bg-muted'"
                ></span>
                <div class="relative z-10 flex items-start justify-between gap-3 w-full">
                  <div>
                    <p class="text-sm font-medium">{{ tab.label }}</p>
                    <p class="text-2xs text-muted-foreground/70 mt-0.5">{{ tab.description }}</p>
                  </div>
                  <span
                    class="mt-1 h-2 w-2 rounded-full"
                    :class="currentTab === tab.key ? 'bg-destructive' : 'bg-muted'"
                  ></span>
                </div>
              </button>
            </div>
          </div>
          <div class="hidden lg:block mt-4 text-xs text-muted-foreground/70">
            更改会自动保存并立即生效。
          </div>
        </aside>

        <section
          class="lg:col-span-9 space-y-6 lg:pl-6 lg:border-l lg:border-border"
          :class="allowScroll ? 'overflow-y-auto min-h-0 pr-1' : ''"
        >
            <Card v-if="currentTab === 'content'" class="settings-card">
              <div class="settings-card-header">
                <div>
                  <h2 class="text-lg font-semibold">内容设置</h2>
                  <p class="text-sm text-muted-foreground">控制敏感内容的展示与提醒方式。</p>
                </div>
                <span class="section-badge">
                  <span class="status-dot" :class="userStatusDotClass"></span>
                  {{ userSaving ? '保存中...' : '自动保存' }}
                </span>
              </div>
              <div class="settings-card-body divide-y divide-border">
                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">显示敏感内容</h3>
                    <p class="setting-desc">显示可能包含成人内容的媒体</p>
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

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">NSFW 视频封面模糊</h3>
                    <p class="setting-desc">自动模糊显示标记为 NSFW 的视频封面</p>
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
            </Card>

            <Card v-if="currentTab === 'playback'" class="settings-card">
              <div class="settings-card-header">
                <div>
                  <h2 class="text-lg font-semibold">播放设置</h2>
                  <p class="text-sm text-muted-foreground">优化播放体验与自动行为。</p>
                </div>
                <span class="section-badge">
                  <span class="status-dot" :class="userStatusDotClass"></span>
                  {{ userSaving ? '保存中...' : '自动保存' }}
                </span>
              </div>
              <div class="settings-card-body divide-y divide-border">
                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">自动播放</h3>
                    <p class="setting-desc">打开视频页面时自动开始播放</p>
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

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">自动播放下一个</h3>
                    <p class="setting-desc">当前视频播放完毕后自动播放下一个视频</p>
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

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">循环播放</h3>
                    <p class="setting-desc">视频播放完毕后自动重新播放</p>
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
            </Card>

            <Card v-if="currentTab === 'system'" class="settings-card">
              <div class="settings-card-header">
                <div>
                  <h2 class="text-lg font-semibold">系统配置</h2>
                  <p class="text-sm text-muted-foreground">影响后台任务与队列消费策略。</p>
                </div>
                <span class="section-badge">
                  <span class="status-dot" :class="systemStatusDotClass"></span>
                  {{ systemStatusLabel }}
                </span>
              </div>
              <div class="settings-card-body divide-y divide-border">
                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">启用调度器（Scheduler）</h3>
                    <p class="setting-desc">按计划任务周期性执行订阅同步、重试等任务</p>
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

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">启用 Worker（队列消费）</h3>
                    <p class="setting-desc">开启后启动 Dramatiq Worker 进行队列消费</p>
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
            </Card>

            <SiteConfigSection v-if="currentTab === 'sites'" />
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useSystemConfig } from '../composables/useSystemConfig';
import { useUserSettings } from '../composables/useUserSettings';
import SiteConfigSection from '@/components/settings/SiteConfigSection.vue';
import { Card } from '@/components/ui/card';
import { Logger } from '@/utils/logger'

// Tabs 配置
const tabs = [
  { key: 'content', label: '内容设置', description: '敏感内容与展示偏好' },
  { key: 'playback', label: '播放设置', description: '播放体验与自动行为' },
  { key: 'system', label: '系统配置', description: '后台任务与服务' },
  { key: 'sites', label: '站点配置', description: '站点来源与采集参数' },
];
const currentTab = ref('content');

// 用户设置
const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings();

// 系统配置
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig();
const systemSaving = ref(false);

const statusLabel = computed(() => {
  if (userSaving.value || systemSaving.value) return '保存中';
  if (systemLoading.value) return '同步中';
  return '自动保存';
});

const statusDotClass = computed(() => {
  if (userSaving.value || systemSaving.value) return 'bg-amber-500 animate-pulse';
  if (systemLoading.value) return 'bg-blue-500 animate-pulse';
  return 'bg-emerald-500';
});

const userStatusDotClass = computed(() => {
  if (userSaving.value) return 'bg-amber-500 animate-pulse';
  return 'bg-emerald-500';
});

const systemStatusDotClass = computed(() => {
  if (systemSaving.value) return 'bg-amber-500 animate-pulse';
  if (systemLoading.value) return 'bg-blue-500 animate-pulse';
  return systemConfig.value ? 'bg-emerald-500' : 'bg-muted';
});

const systemStatusLabel = computed(() => {
  if (systemSaving.value) return '更新中';
  if (systemLoading.value) return '加载中';
  return systemConfig.value ? '已同步' : '未同步';
});

const allowScroll = computed(() => currentTab.value === 'sites');

onMounted(async () => {
  // 加载用户设置
  await loadUserSettings();

  // 加载系统配置
  const result = await loadSystemConfig()
  if (result.error) {
    Logger.error('Failed to load system config', result.error)
  }

});

const onUserSettingChange = async () => {
  await saveUserSettings();
};

const onSystemToggle = async (key, val) => {
  systemSaving.value = true;
  const result = await updateSystemConfig({ [key]: val });
  if (result.error) {
    Logger.error('Failed to update system config', result.error);
  }
  systemSaving.value = false;
};

</script>

<style scoped>
.settings-page {
  font-feature-settings: "tnum";
}

.settings-hero {
  @apply px-1 sm:px-2;
}

.settings-nav {
  @apply shadow-sm;
}

.toolbar-container,
.content-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding-left: 1rem;
  padding-right: 1rem;
  width: 100%;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

.section-badge {
  @apply inline-flex items-center gap-2 text-xs text-muted-foreground/70 bg-card border border-border rounded-full px-3 py-1;
}

.status-dot {
  @apply h-2 w-2 rounded-full;
}

.settings-card {
  border-radius: var(--radius-2xl);
  overflow: hidden;
  background-color: hsl(var(--card));
  background-color: color-mix(in srgb, hsl(var(--card)) 60%, hsl(var(--background)));
  @apply shadow-sm;
}


.settings-card-header {
  @apply flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between px-6 py-4 border-b border-border bg-muted;
}

.settings-card-body {
  @apply px-6 pb-2;
}

.setting-row {
  @apply -mx-6 px-6 flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between transition-colors hover:bg-accent;
}

.setting-text {
  @apply max-w-xl;
}

.setting-title {
  @apply text-sm font-medium text-foreground;
}

.setting-desc {
  @apply text-xs text-muted-foreground;
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
  background-color: hsl(var(--muted));
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
  background-color: hsl(var(--foreground));
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: hsl(var(--destructive));
}

input:checked + .slider:before {
  transform: translateX(24px);
}

input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

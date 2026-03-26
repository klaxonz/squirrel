<template>
  <div class="settings-page bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-4 pb-4">
      <PageHeader
        title="设置"
        description="管理内容偏好、播放体验与系统服务。"
      >
        <template #actions>
          <div class="settings-header-pill">
            <span class="h-2 w-2 rounded-full" :class="statusDotClass"></span>
            <span>{{ statusLabel }}</span>
          </div>
          <div class="settings-header-pill">
            <span class="text-muted-foreground/70">系统配置</span>
            <span class="text-foreground">{{ systemStatusLabel }}</span>
          </div>
        </template>
      </PageHeader>
    </div>

    <div
      class="content-container pb-10 flex-1 min-h-0 overflow-hidden"
    >
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-0 min-h-0 h-full">
        <aside class="lg:col-span-3 lg:sticky lg:top-0 self-start">

          <div class="settings-nav bg-card/80 border border-border rounded-xl p-1.5 lg:rounded-r-none lg:border-r-0">
            <div class="flex lg:flex-col gap-2 overflow-x-auto scrollbar-hide">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                @click="currentTab = tab.key"
                class="tab-button group relative text-left min-w-[10rem] flex-1 lg:flex-none px-3 py-2.5 rounded-lg border transition-colors"
                :class="isCurrentTab(tab.key)
                  ? 'bg-muted border-border text-foreground shadow-sm'
                  : 'bg-transparent border-border text-muted-foreground hover:bg-card/60'"
                :aria-current="isCurrentTab(tab.key) ? 'page' : undefined"
              >
                <span
                  class="tab-accent absolute left-3 top-3 bottom-3 w-0.5 rounded-full transition-opacity"
                  :class="isCurrentTab(tab.key) ? 'opacity-100 bg-primary' : 'opacity-0 bg-muted'"
                ></span>
                <div class="relative z-10 flex items-start justify-between gap-3 w-full">
                  <div>
                    <p class="text-sm font-medium">{{ tab.label }}</p>
                    <p class="text-2xs text-muted-foreground/70 mt-0.5">{{ tab.description }}</p>
                  </div>
                  <span
                    class="mt-1 h-2 w-2 rounded-full"
                    :class="isCurrentTab(tab.key) ? 'bg-primary' : 'bg-muted'"
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
            <Card v-if="isCurrentTab('appearance')" class="settings-card">
              <div class="settings-card-header">
                <div>
                  <h2 class="text-lg font-semibold">外观主题</h2>
                  <p class="text-sm text-muted-foreground">切换浅色、深色或跟随系统主题。</p>
                </div>
                <span class="section-badge">
                  当前生效: {{ effectiveThemeLabel }}
                </span>
              </div>
              <div class="settings-card-body">
                <div class="theme-choice-grid">
                  <button
                    v-for="option in themeOptions"
                    :key="option.value"
                    type="button"
                    class="theme-choice"
                    :class="themeMode === option.value ? 'theme-choice-active' : 'theme-choice-inactive'"
                    @click="setThemeMode(option.value)"
                  >
                    <span class="theme-choice-preview" :class="`theme-choice-preview-${option.value}`">
                      <span class="theme-choice-preview-chip"></span>
                    </span>
                    <span class="theme-choice-copy">
                      <span class="theme-choice-label">{{ option.label }}</span>
                      <span class="theme-choice-desc">{{ option.description }}</span>
                    </span>
                  </button>
                </div>
                <div class="theme-note">
                  <span class="status-dot" :class="themeStatusDotClass"></span>
                  <span>{{ themeStatusText }}</span>
                </div>
              </div>
            </Card>

            <Card v-if="isCurrentTab('content')" class="settings-card">
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
                  <Switch
                    :checked="!!settings.showNsfw"
                    :disabled="userSaving"
                    @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
                  />
                </div>

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">NSFW 视频封面模糊</h3>
                    <p class="setting-desc">自动模糊显示标记为 NSFW 的视频封面</p>
                  </div>
                  <Switch
                    :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                    :disabled="systemLoading || systemSaving"
                    @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
                  />
                </div>
              </div>
            </Card>

            <Card v-if="isCurrentTab('playback')" class="settings-card">
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
                  <Switch
                    :checked="!!settings.autoplay"
                    :disabled="userSaving"
                    @update:checked="(value: boolean) => { settings.autoplay = !!value; onUserSettingChange() }"
                  />
                </div>

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">自动播放下一个</h3>
                    <p class="setting-desc">当前视频播放完毕后自动播放下一个视频</p>
                  </div>
                  <Switch
                    :checked="!!settings.autoplayNext"
                    :disabled="userSaving"
                    @update:checked="(value: boolean) => { settings.autoplayNext = !!value; onUserSettingChange() }"
                  />
                </div>

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">循环播放</h3>
                    <p class="setting-desc">视频播放完毕后自动重新播放</p>
                  </div>
                  <Switch
                    :checked="!!settings.loop"
                    :disabled="userSaving"
                    @update:checked="(value: boolean) => { settings.loop = !!value; onUserSettingChange() }"
                  />
                </div>
              </div>
            </Card>

            <Card v-if="isCurrentTab('system')" class="settings-card">
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
                  <Switch
                    :checked="Boolean(systemConfig?.enable_scheduler)"
                    :disabled="systemLoading || systemSaving"
                    @update:checked="(value: boolean) => onSystemToggle('enable_scheduler', !!value)"
                  />
                </div>

                <div class="setting-row">
                  <div class="setting-text">
                    <h3 class="setting-title">启用 Worker（队列消费）</h3>
                    <p class="setting-desc">开启后启动 Dramatiq Worker 进行队列消费</p>
                  </div>
                  <Switch
                    :checked="Boolean(systemConfig?.enable_worker)"
                    :disabled="systemLoading || systemSaving"
                    @update:checked="(value: boolean) => onSystemToggle('enable_worker', !!value)"
                  />
                </div>
              </div>
            </Card>

            <SiteConfigSection v-if="isCurrentTab('sites')" />
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useSystemConfig } from '../composables/useSystemConfig';
import { useUserSettings } from '../composables/useUserSettings';
import { useAppTheme } from '@/composables/useAppTheme'
import PageHeader from '@/components/layout/PageHeader.vue'
import SiteConfigSection from '@/components/settings/SiteConfigSection.vue';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch'
import { Logger } from '@/utils/logger'
import type { AppThemeMode } from '@/lib/theme'

type SettingsTabKey = 'appearance' | 'content' | 'playback' | 'system' | 'sites'

// Tabs 配置
const tabs: Array<{ key: SettingsTabKey; label: string; description: string }> = [
  { key: 'appearance', label: '外观主题', description: '浅色、深色与系统模式' },
  { key: 'content', label: '内容设置', description: '敏感内容与展示偏好' },
  { key: 'playback', label: '播放设置', description: '播放体验与自动行为' },
  { key: 'system', label: '系统配置', description: '后台任务与服务' },
  { key: 'sites', label: '站点配置', description: '站点来源与采集参数' },
];
const currentTab = ref<SettingsTabKey>('appearance');

const themeOptions: Array<{ value: AppThemeMode; label: string; description: string }> = [
  { value: 'light', label: '浅色', description: '暖灰画布，更适合白天浏览。' },
  { value: 'dark', label: '深色', description: '墨色界面，更适合长时间观看。' },
  { value: 'system', label: '跟随系统', description: '自动匹配当前系统主题。' },
]

const { themeMode, effectiveTheme, setThemeMode } = useAppTheme()

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
  if (userSaving.value || systemSaving.value) return 'bg-warning animate-pulse';
  if (systemLoading.value) return 'bg-info animate-pulse';
  return 'bg-success';
});

const userStatusDotClass = computed(() => {
  if (userSaving.value) return 'bg-warning animate-pulse';
  return 'bg-success';
});

const systemStatusDotClass = computed(() => {
  if (systemSaving.value) return 'bg-warning animate-pulse';
  if (systemLoading.value) return 'bg-info animate-pulse';
  return systemConfig.value ? 'bg-success' : 'bg-muted';
});

const systemStatusLabel = computed(() => {
  if (systemSaving.value) return '更新中';
  if (systemLoading.value) return '加载中';
  return systemConfig.value ? '已同步' : '未同步';
});

const effectiveThemeLabel = computed(() => {
  return effectiveTheme.value === 'dark' ? '深色' : '浅色'
})

const themeStatusText = computed(() => {
  if (themeMode.value === 'system') {
    return `当前跟随系统，正在使用${effectiveThemeLabel.value}主题。`
  }

  return `当前固定使用${effectiveThemeLabel.value}主题。`
})

const themeStatusDotClass = computed(() => {
  return effectiveTheme.value === 'dark' ? 'theme-dot-dark' : 'theme-dot-light'
})

const allowScroll = computed(() => currentTab.value === 'sites');

const isCurrentTab = (tab: SettingsTabKey) => currentTab.value === tab

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

const onSystemToggle = async (key: string, val: boolean) => {
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

.settings-header-pill {
  @apply inline-flex items-center gap-2 text-xs text-muted-foreground/70 bg-card border border-border rounded-md px-3 py-1.5;
}

.settings-nav {
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.035);
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
  @apply inline-flex items-center gap-2 text-xs text-muted-foreground/70 bg-card border border-border rounded-md px-3 py-1;
}

.status-dot {
  @apply h-2 w-2 rounded-full;
}

.settings-card {
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-color: hsl(var(--card));
  background-color: color-mix(in srgb, hsl(var(--card)) 60%, hsl(var(--background)));
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.035);
}


.settings-card-header {
  @apply flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between px-5 py-3.5 border-b border-border bg-secondary/45;
}

.settings-card-body {
  @apply px-5 pb-2;
}

.theme-choice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 0.875rem;
  padding-top: 1.25rem;
  padding-bottom: 1.25rem;
}

.theme-choice {
  display: grid;
  gap: 0.75rem;
  padding: 0.875rem;
  border-radius: calc(var(--radius-lg) - 0.125rem);
  border: 1px solid hsl(var(--border));
  text-align: left;
  background: hsl(var(--card));
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.theme-choice:hover {
  border-color: hsl(var(--ring) / 0.35);
  background: hsl(var(--accent) / 0.45);
}

.theme-choice-active {
  border-color: hsl(var(--ring) / 0.6);
  background: linear-gradient(180deg, hsl(var(--accent) / 0.9), hsl(var(--card)));
  box-shadow: var(--shadow-sm);
}

.theme-choice-inactive {
  box-shadow: none;
}

.theme-choice-preview {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  min-height: 5.5rem;
  padding: 0.75rem;
  border-radius: calc(var(--radius-lg) - 0.125rem);
  border: 1px solid hsl(var(--border) / 0.75);
}

.theme-choice-preview-light {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.08)),
    linear-gradient(135deg, #f7efe6, #e9ded2 55%, #d2bc9e);
}

.theme-choice-preview-dark {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent),
    linear-gradient(145deg, #10161d, #1a232d 58%, #745340);
}

.theme-choice-preview-system {
  background:
    linear-gradient(90deg, #f4ebe0 0 50%, #10161d 50% 100%);
}

.theme-choice-preview-chip {
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  background: linear-gradient(135deg, #cc7a3d, #934125);
  box-shadow: 0 12px 24px rgba(120, 56, 30, 0.28);
}

.theme-choice-copy {
  display: grid;
  gap: 0.2rem;
}

.theme-choice-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.theme-choice-desc {
  font-size: 0.75rem;
  line-height: 1.45;
  color: hsl(var(--muted-foreground));
}

.theme-note {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding-bottom: 1.5rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.theme-dot-light {
  background: #cc7a3d;
}

.theme-dot-dark {
  background: #526a82;
}

.setting-row {
  @apply -mx-5 px-5 flex flex-col gap-3 py-3.5 sm:flex-row sm:items-center sm:justify-between transition-colors hover:bg-accent/45;
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

</style>

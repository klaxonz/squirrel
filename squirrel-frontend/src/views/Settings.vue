<template>
  <div class="settings-page bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-12 pb-12">
      <PageHeader title="系统设置" />
    </div>

    <div
      class="content-container pb-20 flex-1 min-h-0 overflow-hidden"
    >
      <div class="flex flex-col lg:flex-row gap-16 min-h-0 h-full">
        <aside class="lg:w-56 lg:shrink-0 lg:sticky lg:top-0 self-start">
          <nav class="settings-nav space-y-0.5">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="currentTab = tab.key"
              class="tab-button w-full px-4 py-2.5 rounded-xl text-[13px] font-bold transition-all flex items-center gap-3 group relative"
              :class="isCurrentTab(tab.key)
                ? 'text-primary bg-primary/[0.04]'
                : 'text-muted-foreground/60 hover:bg-muted/40 hover:text-foreground'"
              :aria-current="isCurrentTab(tab.key) ? 'page' : undefined"
            >
              <component 
                :is="tab.icon" 
                class="h-4 w-4 shrink-0 transition-transform group-hover:scale-110"
                :class="isCurrentTab(tab.key) ? 'text-primary' : 'text-muted-foreground/40 group-hover:text-muted-foreground/70'"
              />
              <span class="flex-1 text-left">{{ tab.label }}</span>
              <div 
                v-if="isCurrentTab(tab.key)" 
                class="absolute right-2 h-1.5 w-1.5 rounded-full bg-primary"
              ></div>
            </button>
          </nav>
        </aside>

        <section
          class="flex-1 max-w-xl space-y-16"
          :class="allowScroll ? 'overflow-y-auto min-h-0 pr-6 -mr-6' : ''"
        >
            <div v-if="isCurrentTab('appearance')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-2xl font-black tracking-tight text-foreground">外观与主题</h2>
                <p class="text-[13px] text-muted-foreground/50 mt-1 font-medium italic">定制您的视觉体验，选择最适合的主题模式。</p>
              </div>

              <div class="settings-section-content mt-12">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <button
                    v-for="option in themeOptions"
                    :key="option.value"
                    type="button"
                    class="theme-card group"
                    :class="themeMode === option.value ? 'theme-card-active' : 'theme-card-inactive'"
                    @click="setThemeMode(option.value)"
                  >
                    <div class="flex items-center justify-between w-full">
                      <div class="theme-card-icon">
                        <component :is="option.icon" class="h-5 w-5" />
                      </div>
                      <div v-if="themeMode === option.value" class="theme-card-check">
                        <CheckCircle2 class="h-3 w-3" />
                      </div>
                    </div>
                    <div class="mt-4">
                      <div class="text-[14px] font-black tracking-tight">{{ option.label }}</div>
                      <div class="text-[11px] text-muted-foreground/40 font-medium mt-0.5">{{ option.description }}</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <div v-if="isCurrentTab('content')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-2xl font-black tracking-tight text-foreground">内容偏好</h2>
                <p class="text-[13px] text-muted-foreground/50 mt-1 font-medium italic">管理内容展示方式与隐私偏好。</p>
              </div>
              <div class="settings-section-content mt-8">
                <div class="divide-y divide-border/20">
                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">显示敏感内容</h3>
                      <p class="setting-item-desc">启用此项后，将显示标记为 NSFW 的内容。</p>
                    </div>
                    <Switch
                      :checked="!!settings.showNsfw"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
                    />
                  </div>

                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">自动模糊封面</h3>
                      <p class="setting-item-desc">对标记为 NSFW 的封面图进行模糊处理。</p>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="isCurrentTab('playback')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-2xl font-black tracking-tight text-foreground">播放控制</h2>
                <p class="text-[13px] text-muted-foreground/50 mt-1 font-medium italic">配置媒体播放器的交互行为。</p>
              </div>
              <div class="settings-section-content mt-8">
                <div class="divide-y divide-border/20">
                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">进入页面自动播放</h3>
                      <p class="setting-item-desc">进入详情页时立即开始播放视频或音频。</p>
                    </div>
                    <Switch
                      :checked="!!settings.autoplay"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.autoplay = !!value; onUserSettingChange() }"
                    />
                  </div>

                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">自动播放下一个</h3>
                      <p class="setting-item-desc">当前播放结束后，自动跳转并开始播放下一个项目。</p>
                    </div>
                    <Switch
                      :checked="!!settings.autoplayNext"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.autoplayNext = !!value; onUserSettingChange() }"
                    />
                  </div>

                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">循环播放</h3>
                      <p class="setting-item-desc">播放结束后，重新开始播放当前项目。</p>
                    </div>
                    <Switch
                      :checked="!!settings.loop"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.loop = !!value; onUserSettingChange() }"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="isCurrentTab('system')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-2xl font-black tracking-tight text-foreground">核心引擎</h2>
                <p class="text-[13px] text-muted-foreground/50 mt-1 font-medium italic">管理后台服务与核心调度系统。</p>
              </div>
              <div class="settings-section-content mt-8">
                <div class="divide-y divide-border/20">
                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">任务调度器</h3>
                      <p class="setting-item-desc">负责后台任务的定期执行与状态监控。</p>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.enable_scheduler)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('enable_scheduler', !!value)"
                    />
                  </div>

                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">异步工作流</h3>
                      <p class="setting-item-desc">启用异步处理引擎以提高并发处理效率。</p>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.enable_worker)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('enable_worker', !!value)"
                    />
                  </div>
                </div>
              </div>
            </div>

            <SiteConfigSection v-if="isCurrentTab('sites')" />
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { 
  Palette, 
  ShieldCheck, 
  PlayCircle, 
  Settings2, 
  Globe,
  Sun,
  Moon,
  Monitor,
  CheckCircle2,
  RefreshCcw
} from 'lucide-vue-next';
import { useSystemConfig } from '../composables/useSystemConfig';
import { useUserSettings } from '../composables/useUserSettings';
import { useAppTheme } from '@/composables/useAppTheme'
import PageHeader from '@/components/layout/PageHeader.vue'
import SiteConfigSection from '@/components/settings/SiteConfigSection.vue';
import { Switch } from '@/components/ui/switch'
import { Logger } from '@/utils/logger'
import type { AppThemeMode } from '@/lib/theme'

type SettingsTabKey = 'appearance' | 'content' | 'playback' | 'system' | 'sites'

// Tabs 配置
const tabs: Array<{ key: SettingsTabKey; label: string; description: string; icon: any }> = [
  { key: 'appearance', label: '外观主题', description: '外观与主题', icon: Palette },
  { key: 'content', label: '内容设置', description: '内容偏好', icon: ShieldCheck },
  { key: 'playback', label: '播放设置', description: '播放控制', icon: PlayCircle },
  { key: 'system', label: '系统配置', description: '核心引擎', icon: Settings2 },
  { key: 'sites', label: '站点配置', description: '采集源配置', icon: Globe },
];
const currentTab = ref<SettingsTabKey>('appearance');

const themeOptions: Array<{ value: AppThemeMode; label: string; description: string; icon: any }> = [
  { value: 'light', label: '浅色', description: '浅色主题', icon: Sun },
  { value: 'dark', label: '深色', description: '深色主题', icon: Moon },
  { value: 'system', label: '系统', description: '跟随系统', icon: Monitor },
]

const { themeMode, setThemeMode } = useAppTheme()

// 用户设置
const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings();

// 系统配置
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig();
const systemSaving = ref(false);

const allowScroll = computed(() => currentTab.value === 'sites');

const isCurrentTab = (tab: SettingsTabKey) => currentTab.value === tab

onMounted(async () => {
  await loadUserSettings();
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

.toolbar-container,
.content-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-left: 2rem;
  padding-right: 2rem;
  width: 100%;
}

.slide-up {
  animation: slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.settings-section-header {
  @apply pb-6 border-b border-border/20;
}

.theme-card {
  @apply relative flex flex-col p-5 rounded-[24px] border transition-all duration-500 text-left overflow-hidden;
}

.theme-card-active {
  @apply border-primary bg-primary/[0.03] shadow-[0_8px_24px_-12px_hsl(var(--primary)/0.3)];
}

.theme-card-inactive {
  @apply border-border/40 bg-muted/5 hover:border-border/80 hover:bg-muted/20;
}

.theme-card-icon {
  @apply h-10 w-10 rounded-2xl bg-background border border-border/40 flex items-center justify-center text-muted-foreground transition-all duration-500;
}

.theme-card-active .theme-card-icon {
  @apply border-primary/20 bg-primary/10 text-primary rotate-[10deg] scale-110;
}

.theme-card-check {
  @apply h-6 w-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-lg shadow-primary/20;
}

.setting-item {
  @apply flex items-center justify-between py-8 gap-10;
}

.setting-item-copy {
  @apply flex-1 min-w-0;
}

.setting-item-title {
  @apply text-[15px] font-bold text-foreground tracking-tight;
}

.setting-item-desc {
  @apply text-[13px] text-muted-foreground/60 mt-1.5 leading-relaxed;
}
</style>

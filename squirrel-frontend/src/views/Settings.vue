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
              class="tab-button w-full px-3 py-2 rounded-lg text-sm font-semibold transition-all flex items-center gap-3 group relative overflow-hidden"
              :class="isCurrentTab(tab.key)
                ? 'text-primary'
                : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'"
              :aria-current="isCurrentTab(tab.key) ? 'page' : undefined"
            >
              <div 
                v-if="isCurrentTab(tab.key)" 
                class="absolute inset-0 bg-primary/[0.06] transition-opacity"
              ></div>
              <div 
                v-if="isCurrentTab(tab.key)" 
                class="absolute left-0 top-2 bottom-2 w-1 bg-primary rounded-r-full"
              ></div>
              
              <component 
                :is="tab.icon" 
                class="h-4 w-4 shrink-0 z-10"
                :class="isCurrentTab(tab.key) ? 'text-primary' : 'text-muted-foreground/50 group-hover:text-muted-foreground/80'"
              />
              <span class="flex-1 text-left z-10">{{ tab.label }}</span>
            </button>
          </nav>
        </aside>

        <section
          class="flex-1 max-w-xl space-y-16"
          :class="allowScroll ? 'overflow-y-auto min-h-0 pr-6 -mr-6' : ''"
        >
            <div v-if="isCurrentTab('appearance')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-xl font-bold tracking-tight text-foreground">外观与主题</h2>
              </div>

              <div class="settings-section-content mt-10">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <button
                    v-for="option in themeOptions"
                    :key="option.value"
                    type="button"
                    class="theme-card group"
                    :class="themeMode === option.value ? 'theme-card-active' : 'theme-card-inactive'"
                    @click="setThemeMode(option.value)"
                  >
                    <div class="theme-card-icon">
                      <component :is="option.icon" class="h-5 w-5" />
                    </div>
                    <div class="mt-3">
                      <div class="text-[13px] font-bold tracking-tight">{{ option.label }}</div>
                    </div>
                    <div v-if="themeMode === option.value" class="theme-card-check">
                      <CheckCircle2 class="h-3 w-3" />
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <div v-if="isCurrentTab('content')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-xl font-bold tracking-tight text-foreground">内容偏好</h2>
              </div>
              <div class="settings-section-content mt-6">
                <div class="divide-y divide-border/30">
                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">显示敏感内容</h3>
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
                <h2 class="text-xl font-bold tracking-tight text-foreground">播放控制</h2>
              </div>
              <div class="settings-section-content mt-6">
                <div class="divide-y divide-border/30">
                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">进入页面自动播放</h3>
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
                <h2 class="text-xl font-bold tracking-tight text-foreground">核心引擎</h2>
              </div>
              <div class="settings-section-content mt-6">
                <div class="divide-y divide-border/30">
                  <div class="setting-item group">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">任务调度器</h3>
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
  @apply relative flex flex-col p-4 rounded-2xl border transition-all duration-300 text-left overflow-hidden;
}

.theme-card-active {
  @apply border-primary bg-primary/[0.03] shadow-[0_0_0_1px_hsl(var(--primary)/0.1)];
}

.theme-card-inactive {
  @apply border-border/40 bg-muted/10 hover:border-border/80 hover:bg-muted/30;
}

.theme-card-icon {
  @apply h-10 w-10 rounded-xl bg-background border border-border/40 flex items-center justify-center text-muted-foreground transition-all duration-300;
}

.theme-card-active .theme-card-icon {
  @apply border-primary/20 bg-primary/10 text-primary scale-110;
}

.theme-card-check {
  @apply absolute top-3 right-3 h-5 w-5 rounded-full bg-primary text-primary-foreground flex items-center justify-center scale-90;
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

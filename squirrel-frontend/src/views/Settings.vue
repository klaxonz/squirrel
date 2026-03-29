<template>
  <div class="settings-page bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-12 pb-12">
      <PageHeader title="系统设置" />
    </div>

    <div
      class="content-container pb-20 flex-1 min-h-0 overflow-hidden mt-12"
    >
      <div class="flex flex-col lg:flex-row gap-24 min-h-0 h-full">
        <aside class="lg:w-48 lg:shrink-0 lg:sticky lg:top-0 self-start">
          <nav class="settings-nav space-y-8">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="currentTab = tab.key"
              class="tab-button w-full py-2.5 px-4 rounded-xl text-[13px] font-bold tracking-wide transition-all flex items-center gap-3 group relative text-left"
              :class="isCurrentTab(tab.key)
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground/40 hover:text-foreground/60 hover:bg-foreground/[0.02]'"
              :aria-current="isCurrentTab(tab.key) ? 'page' : undefined"
            >
              <component :is="tab.icon" class="h-4 w-4 transition-transform group-hover:scale-110" />
              <span class="flex-1">{{ tab.label }}</span>
              <div 
                v-if="isCurrentTab(tab.key)"
                class="absolute left-0 top-3 bottom-3 w-[2px] bg-primary rounded-full"
              ></div>
            </button>
          </nav>
        </aside>

        <section
          class="flex-1"
          :class="allowScroll ? 'overflow-y-auto min-h-0 pr-6 -mr-6' : ''"
        >
          <Transition name="fade-slide" mode="out-in">
            <div :key="currentTab" class="space-y-24">
              <div v-if="currentTab === 'appearance'" class="settings-section slide-up">
                <div class="settings-section-header flex items-center gap-4 mb-8">
                  <div class="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner">
                    <Palette class="h-6 w-6" />
                  </div>
                  <div>
                    <h2>外观与主题</h2>
                    <p>视觉体验与界面主题</p>
                  </div>
                </div>

                <div class="settings-section-content p-6 rounded-[2rem] bg-card/40 border border-border/10 backdrop-blur-sm">
                  <TransitionGroup name="staggered-reveal" tag="div" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <button
                      v-for="(option, index) in themeOptions"
                      :key="option.value"
                      type="button"
                      class="theme-card relative group p-5 border transition-all duration-300 rounded-2xl flex flex-col items-center justify-center gap-2 overflow-hidden"
                      :class="themeMode === option.value 
                        ? 'border-primary bg-primary/5 shadow-[0_4px_20px_rgba(var(--primary-rgb),0.1)]' 
                        : 'border-border/10 hover:border-border/30 bg-background/40 hover:bg-background/60'"
                      :style="{ '--delay': `${index * 0.1}s` }"
                      @click="setThemeMode(option.value)"
                    >
                      <component :is="option.icon" class="h-5 w-5 mb-1 transition-colors" :class="themeMode === option.value ? 'text-primary' : 'text-muted-foreground/40'" />
                      <div class="text-[13px] font-bold tracking-tight transition-colors" :class="themeMode === option.value ? 'text-primary' : 'text-foreground'">{{ option.label }}</div>
                      <div class="text-[11px] text-muted-foreground/30 font-medium">{{ option.description }}</div>
                      
                      <div 
                        v-if="themeMode === option.value"
                        class="absolute top-2.5 right-2.5"
                      >
                        <CheckCircle2 class="h-3.5 w-3.5 text-primary" />
                      </div>
                    </button>
                  </TransitionGroup>
                </div>
              </div>

              <div v-if="currentTab === 'content'" class="settings-section slide-up">
                <div class="settings-section-header flex items-center gap-4 mb-8">
                  <div class="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner">
                    <ShieldCheck class="h-6 w-6" />
                  </div>
                  <div>
                    <h2>内容偏好</h2>
                    <p>内容偏好与隐私</p>
                  </div>
                </div>
                <div class="settings-section-content rounded-[2rem] bg-card/40 border border-border/10 backdrop-blur-sm overflow-hidden">
                  <TransitionGroup name="staggered-reveal" tag="div" class="divide-y divide-border/5">
                    <div class="setting-item group p-8" :key="'nsfw'" :style="{ '--delay': '0s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">显示敏感内容</h3>
                        <p class="setting-item-desc">启用后将在平台显示标记为敏感内容的内容。</p>
                      </div>
                      <Switch
                        :checked="!!settings.showNsfw"
                        :disabled="userSaving"
                        @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
                      />
                    </div>

                    <div class="setting-item group p-8" :key="'blur'" :style="{ '--delay': '0.1s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">自动模糊封面</h3>
                        <p class="setting-item-desc">在画廊视图中对敏感内容缩略图应用高斯模糊。</p>
                      </div>
                      <Switch
                        :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                        :disabled="systemLoading || systemSaving"
                        @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
                      />
                    </div>
                  </TransitionGroup>
                </div>
              </div>

              <div v-if="currentTab === 'playback'" class="settings-section slide-up">
                <div class="settings-section-header flex items-center gap-4 mb-8">
                  <div class="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner">
                    <PlayCircle class="h-6 w-6" />
                  </div>
                  <div>
                    <h2>播放控制</h2>
                    <p>媒体播放器与交互</p>
                  </div>
                </div>
                <div class="settings-section-content rounded-[2rem] bg-card/40 border border-border/10 backdrop-blur-sm overflow-hidden">
                  <TransitionGroup name="staggered-reveal" tag="div" class="divide-y divide-border/5">
                    <div class="setting-item group p-8" :key="'autoplay'" :style="{ '--delay': '0s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">进入页面自动播放</h3>
                        <p class="setting-item-desc">进入详情页时自动开始媒体播放。</p>
                      </div>
                      <Switch
                        :checked="!!settings.autoplay"
                        :disabled="userSaving"
                        @update:checked="(value: boolean) => { settings.autoplay = !!value; onUserSettingChange() }"
                      />
                    </div>

                    <div class="setting-item group p-8" :key="'autoplayNext'" :style="{ '--delay': '0.1s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">自动播放下一个</h3>
                        <p class="setting-item-desc">按顺序播放当前收藏夹中的项目。</p>
                      </div>
                      <Switch
                        :checked="!!settings.autoplayNext"
                        :disabled="userSaving"
                        @update:checked="(value: boolean) => { settings.autoplayNext = !!value; onUserSettingChange() }"
                      />
                    </div>

                    <div class="setting-item group p-8" :key="'loop'" :style="{ '--delay': '0.2s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">循环播放</h3>
                        <p class="setting-item-desc">播放完成后自动重新开始当前媒体项目。</p>
                      </div>
                      <Switch
                        :checked="!!settings.loop"
                        :disabled="userSaving"
                        @update:checked="(value: boolean) => { settings.loop = !!value; onUserSettingChange() }"
                      />
                    </div>
                  </TransitionGroup>
                </div>
              </div>

              <div v-if="currentTab === 'system'" class="settings-section slide-up">
                <div class="settings-section-header flex items-center gap-4 mb-8">
                  <div class="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner">
                    <Settings2 class="h-6 w-6" />
                  </div>
                  <div>
                    <h2>核心引擎</h2>
                    <p>系统调度与工作引擎</p>
                  </div>
                </div>
                <div class="settings-section-content rounded-[2rem] bg-card/40 border border-border/10 backdrop-blur-sm overflow-hidden">
                  <TransitionGroup name="staggered-reveal" tag="div" class="divide-y divide-border/5">
                    <div class="setting-item group p-8" :key="'scheduler'" :style="{ '--delay': '0s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">任务调度器</h3>
                        <p class="setting-item-desc">后台任务编排与状态同步。</p>
                      </div>
                      <Switch
                        :checked="Boolean(systemConfig?.enable_scheduler)"
                        :disabled="systemLoading || systemSaving"
                        @update:checked="(value: boolean) => onSystemToggle('enable_scheduler', !!value)"
                      />
                    </div>

                    <div class="setting-item group p-8" :key="'worker'" :style="{ '--delay': '0.1s' }">
                      <div class="setting-item-copy">
                        <h3 class="setting-item-title">异步工作流</h3>
                        <p class="setting-item-desc">用于采集任务的高并发处理引擎。</p>
                      </div>
                      <Switch
                        :checked="Boolean(systemConfig?.enable_worker)"
                        :disabled="systemLoading || systemSaving"
                        @update:checked="(value: boolean) => onSystemToggle('enable_worker', !!value)"
                      />
                    </div>
                  </TransitionGroup>
                </div>
              </div>

              <SiteConfigSection v-if="currentTab === 'sites'" />
            </div>
          </Transition>
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
  animation: slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.staggered-reveal-enter-active {
  animation: staggered-reveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

@keyframes staggered-reveal {
  from {
    opacity: 0;
    transform: translateY(20px) rotateX(10deg);
  }
  to {
    opacity: 1;
    transform: translateY(0) rotateX(0);
  }
}

.setting-item {
  @apply relative flex items-center justify-between py-6 px-8 transition-all duration-500;
}

.setting-item:hover {
  @apply bg-foreground/[0.02];
}

.setting-item-copy {
  @apply flex-1 min-w-0 pr-8;
}

.setting-item-title {
  @apply text-[15px] font-bold text-foreground tracking-tight mb-1 transition-colors group-hover:text-primary;
}

.setting-item-desc {
  @apply text-[12px] text-muted-foreground/50 leading-relaxed font-medium;
}

.settings-section-header h2 {
  @apply text-2xl font-black tracking-tight text-foreground;
  font-family: var(--font-sans);
}

.settings-section-header p {
  @apply text-[12px] text-muted-foreground/40 mt-1 font-medium tracking-normal;
}
</style>

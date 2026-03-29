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
              class="tab-button w-full py-1 text-[13px] font-bold tracking-widest uppercase transition-all flex items-center group relative text-left"
              :class="isCurrentTab(tab.key)
                ? 'text-foreground'
                : 'text-muted-foreground/40 hover:text-foreground/60'"
              :aria-current="isCurrentTab(tab.key) ? 'page' : undefined"
            >
              <span class="flex-1">{{ tab.label }}</span>
              <div 
                class="absolute -left-8 top-0 bottom-0 w-[1px] bg-primary transition-transform duration-500 origin-top"
                :class="isCurrentTab(tab.key) ? 'scale-y-100' : 'scale-y-0'"
              ></div>
            </button>
          </nav>
        </aside>

        <section
          class="flex-1 space-y-24"
          :class="allowScroll ? 'overflow-y-auto min-h-0 pr-6 -mr-6' : ''"
        >
            <div v-if="isCurrentTab('appearance')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-3xl font-bold tracking-tighter text-foreground uppercase">外观与主题</h2>
                <p class="text-[11px] text-muted-foreground/30 mt-2 font-bold uppercase tracking-widest">VISUAL EXPERIENCE & INTERFACE THEME</p>
              </div>

              <div class="settings-section-content mt-12 border-t border-border/5">
                <TransitionGroup name="staggered-reveal" tag="div" class="grid grid-cols-1 sm:grid-cols-3">
                  <button
                    v-for="(option, index) in themeOptions"
                    :key="option.value"
                    type="button"
                    class="theme-card"
                    :class="themeMode === option.value ? 'theme-card-active' : 'theme-card-inactive'"
                    :style="{ '--delay': `${index * 0.1}s` }"
                    @click="setThemeMode(option.value)"
                  >
                    <div class="text-[12px] font-bold tracking-widest uppercase">{{ option.label }}</div>
                    <div class="text-[10px] text-muted-foreground/30 font-medium mt-1 uppercase">{{ option.description }}</div>
                    
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-primary transition-transform duration-700 origin-left"
                      :class="themeMode === option.value ? 'scale-x-100' : 'scale-x-0 group-hover:scale-x-50'"></div>
                  </button>
                </TransitionGroup>
              </div>
            </div>

            <div v-if="isCurrentTab('content')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-3xl font-bold tracking-tighter text-foreground uppercase">内容偏好</h2>
                <p class="text-[11px] text-muted-foreground/30 mt-2 font-bold uppercase tracking-widest">CONTENT PREFERENCES & PRIVACY</p>
              </div>
              <div class="settings-section-content mt-12 border-t border-border/5">
                <TransitionGroup name="staggered-reveal" tag="div" class="divide-y divide-border/5">
                  <div class="setting-item" :key="'nsfw'" :style="{ '--delay': '0s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">显示敏感内容</h3>
                      <p class="setting-item-desc">Enable to display content marked as NSFW across the platform.</p>
                    </div>
                    <Switch
                      :checked="!!settings.showNsfw"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>

                  <div class="setting-item" :key="'blur'" :style="{ '--delay': '0.1s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">自动模糊封面</h3>
                      <p class="setting-item-desc">Apply Gaussian blur to NSFW thumbnails in gallery views.</p>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>
                </TransitionGroup>
              </div>
            </div>

            <div v-if="isCurrentTab('playback')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-3xl font-bold tracking-tighter text-foreground uppercase">播放控制</h2>
                <p class="text-[11px] text-muted-foreground/30 mt-2 font-bold uppercase tracking-widest">MEDIA PLAYER & INTERACTION</p>
              </div>
              <div class="settings-section-content mt-12 border-t border-border/5">
                <TransitionGroup name="staggered-reveal" tag="div" class="divide-y divide-border/5">
                  <div class="setting-item" :key="'autoplay'" :style="{ '--delay': '0s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">进入页面自动播放</h3>
                      <p class="setting-item-desc">Automatically start media playback when entering detail pages.</p>
                    </div>
                    <Switch
                      :checked="!!settings.autoplay"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.autoplay = !!value; onUserSettingChange() }"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>

                  <div class="setting-item" :key="'autoplayNext'" :style="{ '--delay': '0.1s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">自动播放下一个</h3>
                      <p class="setting-item-desc">Sequential playback of items in the current collection.</p>
                    </div>
                    <Switch
                      :checked="!!settings.autoplayNext"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.autoplayNext = !!value; onUserSettingChange() }"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>

                  <div class="setting-item" :key="'loop'" :style="{ '--delay': '0.2s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">循环播放</h3>
                      <p class="setting-item-desc">Restart current media item automatically upon completion.</p>
                    </div>
                    <Switch
                      :checked="!!settings.loop"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.loop = !!value; onUserSettingChange() }"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>
                </TransitionGroup>
              </div>
            </div>

            <div v-if="isCurrentTab('system')" class="settings-section slide-up">
              <div class="settings-section-header">
                <h2 class="text-3xl font-bold tracking-tighter text-foreground uppercase">核心引擎</h2>
                <p class="text-[11px] text-muted-foreground/30 mt-2 font-bold uppercase tracking-widest">SYSTEM SCHEDULER & WORKER ENGINE</p>
              </div>
              <div class="settings-section-content mt-12 border-t border-border/5">
                <TransitionGroup name="staggered-reveal" tag="div" class="divide-y divide-border/5">
                  <div class="setting-item" :key="'scheduler'" :style="{ '--delay': '0s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">任务调度器</h3>
                      <p class="setting-item-desc">Background task orchestration and state synchronization.</p>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.enable_scheduler)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('enable_scheduler', !!value)"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>

                  <div class="setting-item" :key="'worker'" :style="{ '--delay': '0.1s' }">
                    <div class="setting-item-copy">
                      <h3 class="setting-item-title">异步工作流</h3>
                      <p class="setting-item-desc">High-concurrency processing engine for extraction tasks.</p>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.enable_worker)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('enable_worker', !!value)"
                    />
                    <div class="absolute top-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                    <div class="absolute bottom-0 left-0 right-0 h-[1px] bg-foreground/5 transition-transform duration-700 scale-x-0 group-hover:scale-x-100 origin-center"></div>
                  </div>
                </TransitionGroup>
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
  animation: slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.staggered-reveal-enter-active {
  animation: staggered-reveal 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay);
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
</style>

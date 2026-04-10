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

              <div v-if="currentTab === 'security'" class="settings-section slide-up">
                <div class="settings-section-header flex items-center gap-4 mb-8">
                  <div class="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner">
                    <KeyRound class="h-6 w-6" />
                  </div>
                  <div>
                    <h2>账户安全</h2>
                    <p>密码更新与会话撤销</p>
                  </div>
                </div>

                <div class="space-y-6">
                  <Alert v-if="securityError" variant="destructive">
                    <AlertDescription>{{ securityError }}</AlertDescription>
                  </Alert>

                  <Alert v-if="securitySuccess">
                    <AlertDescription>{{ securitySuccess }}</AlertDescription>
                  </Alert>

                  <div class="security-card">
                    <div class="security-card__copy">
                      <div class="security-card__eyebrow">
                        <ShieldAlert class="h-4 w-4" />
                        <span>密码轮换</span>
                      </div>
                      <h3 class="security-card__title">修改登录密码</h3>
                      <p class="security-card__desc">修改后，服务端会自动废弃此前签发的旧 token，只保留当前这个会话。</p>
                    </div>

                    <form class="security-form" @submit.prevent="handlePasswordUpdate">
                      <label class="security-field">
                        <span class="security-field__label">当前密码</span>
                        <input
                          v-model="securityForm.currentPassword"
                          type="password"
                          autocomplete="current-password"
                          class="security-field__input"
                          :disabled="passwordSubmitting"
                        />
                      </label>

                      <label class="security-field">
                        <span class="security-field__label">新密码</span>
                        <input
                          v-model="securityForm.newPassword"
                          type="password"
                          autocomplete="new-password"
                          class="security-field__input"
                          :disabled="passwordSubmitting"
                        />
                      </label>

                      <label class="security-field">
                        <span class="security-field__label">确认新密码</span>
                        <input
                          v-model="securityForm.confirmPassword"
                          type="password"
                          autocomplete="new-password"
                          class="security-field__input"
                          :disabled="passwordSubmitting"
                        />
                      </label>

                      <div class="security-actions">
                        <Button type="submit" :disabled="passwordSubmitting" class="min-w-[7rem]">
                          {{ passwordSubmitting ? '提交中...' : '更新密码' }}
                        </Button>
                      </div>
                    </form>
                  </div>

                  <div class="security-card security-card--compact">
                    <div class="security-card__copy">
                      <div class="security-card__eyebrow">
                        <LogOut class="h-4 w-4" />
                        <span>会话撤销</span>
                      </div>
                      <h3 class="security-card__title">注销其他设备</h3>
                      <p class="security-card__desc">如果怀疑 token 泄露，可以立即让其他浏览器或设备上的旧登录态失效，当前页面会自动续签新 token。</p>
                    </div>

                    <div class="security-actions">
                      <Button
                        type="button"
                        variant="outline"
                        :disabled="sessionSubmitting"
                        @click="handleRevokeSessions"
                      >
                        {{ sessionSubmitting ? '处理中...' : '撤销其他会话' }}
                      </Button>
                    </div>
                  </div>
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
import { computed, onMounted, ref } from 'vue';
import { 
  CheckCircle2,
  Globe,
  KeyRound,
  LogOut,
  Monitor,
  Moon,
  Palette,
  PlayCircle,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Sun,
} from 'lucide-vue-next';
import { revokeUserSessions, updateUserPassword } from '@/api'
import PageHeader from '@/components/layout/PageHeader.vue'
import SiteConfigSection from '@/components/settings/SiteConfigSection.vue';
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useAppTheme } from '@/composables/useAppTheme'
import type { AppThemeMode } from '@/lib/theme'
import { Logger } from '@/utils/logger'
import { useSystemConfig } from '../composables/useSystemConfig';
import { useUserSettings } from '../composables/useUserSettings';

type SettingsTabKey = 'appearance' | 'content' | 'playback' | 'security' | 'system' | 'sites'

// Tabs 配置
const tabs: Array<{ key: SettingsTabKey; label: string; description: string; icon: any }> = [
  { key: 'appearance', label: '外观主题', description: '外观与主题', icon: Palette },
  { key: 'content', label: '内容设置', description: '内容偏好', icon: ShieldCheck },
  { key: 'playback', label: '播放设置', description: '播放控制', icon: PlayCircle },
  { key: 'security', label: '账户安全', description: '密码与会话', icon: KeyRound },
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
const passwordSubmitting = ref(false)
const sessionSubmitting = ref(false)
const securityError = ref('')
const securitySuccess = ref('')
const securityForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const allowScroll = computed(() => currentTab.value === 'sites');

const isCurrentTab = (tab: SettingsTabKey) => currentTab.value === tab

const resetSecurityFeedback = () => {
  securityError.value = ''
  securitySuccess.value = ''
}

const getErrorMessage = (error: any, fallback: string) => {
  if (!error) return fallback
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string') return error.message
  return fallback
}

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

const handlePasswordUpdate = async () => {
  resetSecurityFeedback()

  if (!securityForm.value.currentPassword || !securityForm.value.newPassword || !securityForm.value.confirmPassword) {
    securityError.value = '请完整填写密码信息'
    return
  }

  if (securityForm.value.newPassword.length < 8) {
    securityError.value = '新密码至少需要 8 位'
    return
  }

  if (securityForm.value.newPassword !== securityForm.value.confirmPassword) {
    securityError.value = '两次输入的新密码不一致'
    return
  }

  passwordSubmitting.value = true
  try {
    const result = await updateUserPassword({
      current_password: securityForm.value.currentPassword,
      new_password: securityForm.value.newPassword,
    })
    if (result.error) {
      securityError.value = getErrorMessage(result.error, '密码更新失败')
      return
    }

    securitySuccess.value = '密码已更新，旧 token 已失效'
    securityForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    }
  } finally {
    passwordSubmitting.value = false
  }
}

const handleRevokeSessions = async () => {
  resetSecurityFeedback()
  sessionSubmitting.value = true
  try {
    const result = await revokeUserSessions()
    if (result.error) {
      securityError.value = getErrorMessage(result.error, '撤销会话失败')
      return
    }

    securitySuccess.value = '其他设备上的旧登录态已失效'
  } finally {
    sessionSubmitting.value = false
  }
}

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

.security-card {
  @apply rounded-[2rem] border border-border/10 bg-card/40 p-8 backdrop-blur-sm;
}

.security-card--compact {
  @apply flex flex-col gap-6 md:flex-row md:items-end md:justify-between;
}

.security-card__copy {
  @apply space-y-3;
}

.security-card__eyebrow {
  @apply inline-flex items-center gap-2 rounded-full border border-border/15 bg-background/40 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground/60;
}

.security-card__title {
  @apply text-lg font-black tracking-tight text-foreground;
}

.security-card__desc {
  @apply max-w-2xl text-sm leading-relaxed text-muted-foreground/70;
}

.security-form {
  @apply mt-8 grid gap-4;
}

.security-field {
  @apply grid gap-2;
}

.security-field__label {
  @apply text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground/55;
}

.security-field__input {
  @apply h-11 rounded-2xl border border-border/15 bg-background/50 px-4 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/30 focus:border-primary/40 focus:bg-background;
}

.security-actions {
  @apply flex flex-wrap items-center gap-3 pt-2;
}
</style>

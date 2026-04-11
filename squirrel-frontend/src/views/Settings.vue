<template>
  <div class="settings-page bg-background text-foreground min-h-full">
    <!-- Header -->
    <header class="settings-header">
      <div class="settings-header__inner">
        <div class="settings-header__copy">
          <h1 class="settings-header__title">设置</h1>
          <p class="settings-header__desc">配置你的偏好与账户</p>
        </div>
        <div v-if="hasUnsavedChanges" class="settings-header__status">
          <span class="status-dot"></span>
          <span class="status-text">有未保存的更改</span>
        </div>
      </div>
    </header>

    <!-- Tab Navigation -->
    <nav class="settings-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        role="tab"
        :aria-selected="currentTab === tab.key"
        :aria-controls="`panel-${tab.key}`"
        class="settings-tab"
        :class="{ 'settings-tab--active': currentTab === tab.key }"
        @click="currentTab = tab.key"
      >
        <component :is="tab.icon" class="settings-tab__icon" />
        <span class="settings-tab__label">{{ tab.label }}</span>
      </button>
    </nav>

    <!-- Content Panel -->
    <main class="settings-content">
      <div
        v-if="currentTab === 'appearance'"
        role="tabpanel"
        :id="`panel-appearance`"
        class="settings-panel"
      >
        <!-- Section: Theme -->
        <section class="settings-section">
          <div class="settings-section__header">
            <div class="settings-section__icon">
              <Palette class="h-5 w-5" />
            </div>
            <div class="settings-section__meta">
              <h2 class="settings-section__title">主题</h2>
              <p class="settings-section__desc">选择界面外观</p>
            </div>
          </div>

          <div class="theme-grid">
            <button
              v-for="option in themeOptions"
              :key="option.value"
              type="button"
              class="theme-option"
              :class="{ 'theme-option--active': themeMode === option.value }"
              @click="setThemeMode(option.value)"
            >
              <div class="theme-option__preview" :class="`theme-option__preview--${option.value}`">
                <div class="theme-option__preview-inner">
                  <component :is="option.icon" class="h-4 w-4" />
                </div>
              </div>
              <div class="theme-option__info">
                <span class="theme-option__name">{{ option.label }}</span>
                <span class="theme-option__type">{{ option.description }}</span>
              </div>
              <div v-if="themeMode === option.value" class="theme-option__check">
                <Check class="h-3.5 w-3.5" />
              </div>
            </button>
          </div>
        </section>
      </div>

      <div
        v-if="currentTab === 'content'"
        role="tabpanel"
        :id="`panel-content`"
        class="settings-panel"
      >
        <section class="settings-section">
          <div class="settings-section__header">
            <div class="settings-section__icon">
              <ShieldCheck class="h-5 w-5" />
            </div>
            <div class="settings-section__meta">
              <h2 class="settings-section__title">内容与隐私</h2>
              <p class="settings-section__desc">控制内容展示偏好</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">显示敏感内容</h3>
                <p class="settings-row__desc">启用后在平台显示标记为敏感的内容</p>
              </div>
              <Switch
                :checked="!!settings.showNsfw"
                :disabled="userSaving"
                @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
              />
            </div>

            <div class="settings-divider"></div>

            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">自动模糊封面</h3>
                <p class="settings-row__desc">对敏感内容缩略图应用模糊效果</p>
              </div>
              <Switch
                :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                :disabled="systemLoading || systemSaving"
                @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
              />
            </div>
          </div>
        </section>
      </div>

      <div
        v-if="currentTab === 'playback'"
        role="tabpanel"
        :id="`panel-playback`"
        class="settings-panel"
      >
        <section class="settings-section">
          <div class="settings-section__header">
            <div class="settings-section__icon">
              <PlayCircle class="h-5 w-5" />
            </div>
            <div class="settings-section__meta">
              <h2 class="settings-section__title">播放控制</h2>
              <p class="settings-section__desc">管理媒体播放行为</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">自动播放</h3>
                <p class="settings-row__desc">进入详情页时自动开始播放</p>
              </div>
              <Switch
                :checked="!!settings.autoplay"
                :disabled="userSaving"
                @update:checked="(value: boolean) => { settings.autoplay = !!value; onUserSettingChange() }"
              />
            </div>

            <div class="settings-divider"></div>

            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">自动播放下一个</h3>
                <p class="settings-row__desc">当前播放完成后自动播放下一项</p>
              </div>
              <Switch
                :checked="!!settings.autoplayNext"
                :disabled="userSaving"
                @update:checked="(value: boolean) => { settings.autoplayNext = !!value; onUserSettingChange() }"
              />
            </div>

            <div class="settings-divider"></div>

            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">循环播放</h3>
                <p class="settings-row__desc">播放完成后重新开始当前项目</p>
              </div>
              <Switch
                :checked="!!settings.loop"
                :disabled="userSaving"
                @update:checked="(value: boolean) => { settings.loop = !!value; onUserSettingChange() }"
              />
            </div>
          </div>
        </section>
      </div>

      <div
        v-if="currentTab === 'security'"
        role="tabpanel"
        :id="`panel-security`"
        class="settings-panel"
      >
        <section class="settings-section">
          <div class="settings-section__header">
            <div class="settings-section__icon">
              <KeyRound class="h-5 w-5" />
            </div>
            <div class="settings-section__meta">
              <h2 class="settings-section__title">账户安全</h2>
              <p class="settings-section__desc">密码与会话管理</p>
            </div>
          </div>

          <div v-if="securityError" class="settings-alert settings-alert--error">
            <AlertCircle class="h-4 w-4" />
            <span>{{ securityError }}</span>
          </div>

          <div v-if="securitySuccess" class="settings-alert settings-alert--success">
            <CheckCircle2 class="h-4 w-4" />
            <span>{{ securitySuccess }}</span>
          </div>

          <div class="settings-card settings-card--form">
            <div class="settings-card__label">
              <ShieldAlert class="h-4 w-4" />
              <span>修改密码</span>
            </div>
            <p class="settings-card__note">修改密码后，系统会自动使其他设备上的会话失效。</p>

            <form class="security-form" @submit.prevent="handlePasswordUpdate">
              <div class="form-field">
                <label class="form-field__label">当前密码</label>
                <input
                  v-model="securityForm.currentPassword"
                  type="password"
                  autocomplete="current-password"
                  class="form-field__input"
                  :disabled="passwordSubmitting"
                  placeholder="输入当前密码"
                />
              </div>

              <div class="form-field">
                <label class="form-field__label">新密码</label>
                <input
                  v-model="securityForm.newPassword"
                  type="password"
                  autocomplete="new-password"
                  class="form-field__input"
                  :disabled="passwordSubmitting"
                  placeholder="输入新密码（至少8位）"
                />
              </div>

              <div class="form-field">
                <label class="form-field__label">确认密码</label>
                <input
                  v-model="securityForm.confirmPassword"
                  type="password"
                  autocomplete="new-password"
                  class="form-field__input"
                  :disabled="passwordSubmitting"
                  placeholder="再次输入新密码"
                />
              </div>

              <div class="form-actions">
                <Button
                  type="submit"
                  :disabled="passwordSubmitting"
                  size="sm"
                >
                  {{ passwordSubmitting ? '更新中...' : '更新密码' }}
                </Button>
              </div>
            </form>
          </div>

          <div class="settings-card settings-card--compact">
            <div class="settings-card__copy">
              <div class="settings-card__label settings-card__label--inline">
                <LogOut class="h-4 w-4" />
                <span>撤销会话</span>
              </div>
              <h3 class="settings-card__title">注销其他设备</h3>
              <p class="settings-card__desc">使其他浏览器或设备上的登录态失效</p>
            </div>
            <Button
              variant="outline"
              :disabled="sessionSubmitting"
              size="sm"
              @click="handleRevokeSessions"
            >
              {{ sessionSubmitting ? '处理中...' : '撤销会话' }}
            </Button>
          </div>
        </section>
      </div>

      <div
        v-if="currentTab === 'system'"
        role="tabpanel"
        :id="`panel-system`"
        class="settings-panel"
      >
        <section class="settings-section">
          <div class="settings-section__header">
            <div class="settings-section__icon">
              <Settings2 class="h-5 w-5" />
            </div>
            <div class="settings-section__meta">
              <h2 class="settings-section__title">系统引擎</h2>
              <p class="settings-section__desc">后台调度与工作进程</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">任务调度器</h3>
                <p class="settings-row__desc">后台任务编排与状态同步引擎</p>
              </div>
              <Switch
                :checked="Boolean(systemConfig?.enable_scheduler)"
                :disabled="systemLoading || systemSaving"
                @update:checked="(value: boolean) => onSystemToggle('enable_scheduler', !!value)"
              />
            </div>

            <div class="settings-divider"></div>

            <div class="settings-row">
              <div class="settings-row__info">
                <h3 class="settings-row__title">异步工作流</h3>
                <p class="settings-row__desc">用于采集任务的高并发处理引擎</p>
              </div>
              <Switch
                :checked="Boolean(systemConfig?.enable_worker)"
                :disabled="systemLoading || systemSaving"
                @update:checked="(value: boolean) => onSystemToggle('enable_worker', !!value)"
              />
            </div>
          </div>
        </section>
      </div>

      <div
        v-if="currentTab === 'sites'"
        role="tabpanel"
        :id="`panel-sites`"
        class="settings-panel"
      >
        <SiteConfigSection />
      </div>
    </main>

    <!-- Save Feedback Toast -->
    <Transition name="toast">
      <div v-if="saveToastVisible" class="save-toast" :class="saveToastClass">
        <CheckCircle2 v-if="!saveToastError" class="h-4 w-4" />
        <AlertCircle v-else class="h-4 w-4" />
        <span>{{ saveToastMessage }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Globe,
  KeyRound,
  LogOut,
  Monitor,
  Moon,
  Palette,
  PlayCircle,
  Rocket,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Sun,
  Zap,
} from 'lucide-vue-next';
import { revokeUserSessions, updateUserPassword } from '@/api'
import SiteConfigSection from '@/components/settings/SiteConfigSection.vue';
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useAppTheme } from '@/composables/useAppTheme'
import type { AppThemeMode } from '@/lib/theme'
import { Logger } from '@/utils/logger'
import { useSystemConfig } from '../composables/useSystemConfig';
import { useUserSettings } from '../composables/useUserSettings';

type SettingsTabKey = 'appearance' | 'content' | 'playback' | 'security' | 'system' | 'sites'

const tabs: Array<{ key: SettingsTabKey; label: string; icon: any }> = [
  { key: 'appearance', label: '外观', icon: Palette },
  { key: 'content', label: '内容', icon: ShieldCheck },
  { key: 'playback', label: '播放', icon: PlayCircle },
  { key: 'security', label: '安全', icon: KeyRound },
  { key: 'system', label: '系统', icon: Settings2 },
  { key: 'sites', label: '站点', icon: Globe },
];
const currentTab = ref<SettingsTabKey>('appearance');

const themeOptions: Array<{ value: AppThemeMode; label: string; description: string; icon: any }> = [
  { value: 'light', label: '浅色', description: '明亮的浅色主题', icon: Sun },
  { value: 'dark', label: '深色', description: '护眼的深色主题', icon: Moon },
  { value: 'system', label: '系统', description: '跟随系统设置', icon: Monitor },
  { value: 'cyber', label: '赛博', description: '霓虹工业风', icon: Zap },
  { value: 'scifi', label: '科幻', description: '星际流体风格', icon: Rocket },
]

const { themeMode, setThemeMode } = useAppTheme()

// User settings
const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings();

// System config
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig();
const systemSaving = ref(false)
const passwordSubmitting = ref(false)
const sessionSubmitting = ref(false)
const securityError = ref('')
const securitySuccess = ref('')
const securityForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

// Save toast
const saveToastVisible = ref(false)
const saveToastMessage = ref('')
const saveToastError = ref(false)
const saveToastClass = computed(() => saveToastError.value ? 'save-toast--error' : 'save-toast--success')
const hasUnsavedChanges = ref(false)

let saveToastTimer: ReturnType<typeof setTimeout> | null = null

const showSaveToast = (message: string, isError = false) => {
  if (saveToastTimer) {
    clearTimeout(saveToastTimer)
  }
  saveToastMessage.value = message
  saveToastError.value = isError
  saveToastVisible.value = true
  saveToastTimer = setTimeout(() => {
    saveToastVisible.value = false
  }, 3000)
}

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
  userSaving.value = true;
  hasUnsavedChanges.value = true;
  try {
    await saveUserSettings();
    showSaveToast('已保存');
  } catch (err) {
    showSaveToast('保存失败', true);
  } finally {
    userSaving.value = false;
    hasUnsavedChanges.value = false;
  }
};

const onSystemToggle = async (key: string, val: boolean) => {
  systemSaving.value = true;
  const result = await updateSystemConfig({ [key]: val });
  if (result.error) {
    showSaveToast('保存失败', true);
    Logger.error('Failed to update system config', result.error);
  } else {
    showSaveToast('已保存');
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

    securitySuccess.value = '密码已更新，其他设备会话已失效'
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

    securitySuccess.value = '其他设备上的登录态已失效'
  } finally {
    sessionSubmitting.value = false
  }
}
</script>

<style scoped>
.settings-page {
  font-feature-settings: "tnum";
}

/* Header */
.settings-header {
  padding: 1rem 2rem 0;
}

@media (min-width: 640px) {
  .settings-header {
    padding: 1.5rem 2rem 0;
  }
}

@media (min-width: 1024px) {
  .settings-header {
    padding: 2rem 2rem 0;
  }
}

@media (max-width: 768px) {
  .settings-header {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

.settings-header__inner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.settings-header__title {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: hsl(var(--foreground));
  margin: 0;
}

.settings-header__desc {
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  margin: 0.25rem 0 0;
}

.settings-header__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: hsl(var(--warning) / 0.1);
  border: 1px solid hsl(var(--warning) / 0.2);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--warning));
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: hsl(var(--warning));
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Tab Navigation */
.settings-tabs {
  display: flex;
  gap: 0.25rem;
  padding: 1.5rem 2rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  overflow-x: auto;
  scrollbar-width: none;
}

@media (max-width: 768px) {
  .settings-tabs {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

.settings-tabs::-webkit-scrollbar {
  display: none;
}

.settings-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.settings-tab:hover {
  color: hsl(var(--foreground));
}

.settings-tab--active {
  color: hsl(var(--primary));
  border-bottom-color: hsl(var(--primary));
}

.settings-tab__icon {
  width: 1rem;
  height: 1rem;
}

.settings-tab__badge {
  padding: 0.125rem 0.375rem;
  font-size: 0.625rem;
  font-weight: 700;
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  border-radius: 9999px;
}

/* Content */
.settings-content {
  padding: 1.5rem 2rem 3rem;
  max-width: 1200px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .settings-content {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

@media (min-width: 640px) {
  .settings-content {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .settings-content {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

.settings-panel {
  animation: fade-in 0.3s ease;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Section */
.settings-section {
  margin-bottom: 2rem;
}

.settings-section__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.settings-section__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  border-radius: 0.75rem;
}

.settings-section__title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0;
}

.settings-section__desc {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin: 0.125rem 0 0;
}

/* Theme Grid */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.theme-option:hover {
  border-color: hsl(var(--primary) / 0.3);
  transform: translateY(-2px);
}

.theme-option--active {
  border-color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.05);
}

.theme-option__preview {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-option__preview--light {
  background: linear-gradient(135deg, #fafafa 0%, #e8e8e8 100%);
  color: #333;
}

.theme-option__preview--dark {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #f0f0f0;
}

.theme-option__preview--system {
  background: linear-gradient(135deg, #fafafa 0%, #1a1a2e 100%);
  color: #666;
}

.theme-option__preview--cyber {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
  color: #FF4F00;
}

.theme-option__preview--scifi {
  background: linear-gradient(135deg, #05080a 0%, #0a1628 100%);
  color: #00E5FF;
}

.theme-option__preview-inner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-option__info {
  text-align: center;
}

.theme-option__name {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.theme-option__type {
  display: block;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
}

.theme-option__check {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  color: hsl(var(--primary));
}

/* Settings Card */
.settings-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 1rem;
  overflow: hidden;
}

.settings-card--form {
  padding: 1.25rem;
}

.settings-card--compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem;
}

.settings-card__label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: hsl(var(--muted-foreground));
  background: hsl(var(--secondary));
  border-radius: 9999px;
  margin-bottom: 0.75rem;
}

.settings-card__label--inline {
  margin-bottom: 0.5rem;
}

.settings-card__note {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin: 0 0 1rem;
}

.settings-card__copy {
  flex: 1;
}

.settings-card__title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0;
}

.settings-card__desc {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin: 0.25rem 0 0;
}

/* Settings Row */
.settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  transition: background 0.15s ease;
}

.settings-row:hover {
  background: hsl(var(--secondary) / 0.3);
}

.settings-row__info {
  flex: 1;
  min-width: 0;
}

.settings-row__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.settings-row__desc {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin: 0.125rem 0 0;
}

.settings-divider {
  height: 1px;
  background: hsl(var(--border) / 0.5);
  margin: 0 1.25rem;
}

/* Alert */
.settings-alert {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  margin-bottom: 1rem;
}

.settings-alert--error {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
  border: 1px solid hsl(var(--destructive) / 0.2);
}

.settings-alert--success {
  background: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
  border: 1px solid hsl(var(--success) / 0.2);
}

/* Security Form */
.security-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
}

.form-field__input {
  height: 2.5rem;
  padding: 0 0.875rem;
  font-size: 0.875rem;
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: 0.625rem;
  outline: none;
  transition: all 0.15s ease;
}

.form-field__input:focus {
  border-color: hsl(var(--primary));
  box-shadow: 0 0 0 3px hsl(var(--primary) / 0.1);
}

.form-field__input::placeholder {
  color: hsl(var(--muted-foreground) / 0.5);
}

.form-field__input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}

/* Toast */
.save-toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  border-radius: 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  box-shadow: 0 10px 40px hsl(var(--foreground) / 0.2);
  z-index: 100;
}

.save-toast--error {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}

.save-toast--success {
  background: hsl(var(--foreground));
  color: hsl(var(--background));
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(1rem) scale(0.95);
}

/* Responsive */
@media (max-width: 768px) {
  .settings-header,
  .settings-tabs,
  .settings-content {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .theme-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .settings-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .settings-card--compact {
    flex-direction: column;
    align-items: flex-start;
  }

  .save-toast {
    left: 1rem;
    right: 1rem;
    bottom: 1rem;
  }
}
</style>

<template>
  <AppPageShell variant="compact">
    <div class="flex h-full overflow-hidden bg-background text-foreground">
      <aside class="hidden w-72 shrink-0 flex-col border-r border-border/50 bg-background lg:flex">
        <div class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4">
          <div class="min-w-0">
            <h1 class="truncate text-sm font-semibold">设置</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ activeTab.label }}</p>
          </div>
          <span v-if="hasUnsavedChanges" class="inline-flex h-7 items-center rounded-md border border-border/50 bg-muted px-2 text-xs text-muted-foreground">
            保存中
          </span>
        </div>

        <nav class="flex-1 space-y-1 overflow-y-auto p-2 custom-scrollbar">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            @click="navigateToTab(tab.path)"
            class="flex h-10 w-full items-center gap-2 rounded-md px-2 text-left text-sm font-medium transition-colors"
            :class="currentTab === tab.key ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
          >
            <AppIcon :name="tab.icon" class="h-4 w-4" />
            <span class="min-w-0 flex-1 truncate">{{ tab.label }}</span>
            <span v-if="tab.badge" class="text-xs font-normal text-muted-foreground">{{ tab.badge }}</span>
          </button>
        </nav>
      </aside>

      <main class="flex min-w-0 flex-1 flex-col bg-background">
        <header class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4 lg:px-6">
          <div class="min-w-0">
            <h2 class="truncate text-base font-semibold">{{ activeTab.label }}</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ activeTabDescription }}</p>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <span v-if="hasUnsavedChanges" class="hidden h-7 items-center rounded-md border border-border/50 bg-muted px-2 text-xs text-muted-foreground sm:inline-flex">
              保存中
            </span>
          </div>
        </header>

        <div class="shrink-0 border-b border-border/50 p-2 lg:hidden">
          <div class="flex overflow-x-auto rounded-md bg-muted p-0.5 custom-scrollbar">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="navigateToTab(tab.path)"
              class="h-8 shrink-0 rounded-[6px] px-3 text-sm font-medium transition-colors"
              :class="currentTab === tab.key ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <main class="mx-auto w-full max-w-[960px] p-4 lg:p-6">
            <div v-if="pageLoading" class="space-y-3">
              <div class="h-12 animate-pulse rounded-lg bg-accent/30" />
              <div class="h-48 animate-pulse rounded-lg bg-accent/25" />
              <div class="h-36 animate-pulse rounded-lg bg-accent/20" />
            </div>

            <div v-else class="space-y-6">
              <section v-if="currentTab === 'appearance'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>界面外观</h3>
                  <p>选择偏好的视觉主题。</p>
                </div>

                <div class="grid gap-3 sm:grid-cols-3">
                  <button
                    v-for="option in themeOptions"
                    :key="option.value"
                    @click="setThemeMode(option.value)"
                    class="group relative flex min-h-28 flex-col justify-between rounded-lg border p-4 text-left transition-colors"
                    :class="themeMode === option.value ? 'border-foreground/20 bg-accent/40 text-foreground' : 'border-border/50 bg-background hover:bg-accent/30'"
                  >
                    <div class="flex items-center justify-between">
                      <span class="flex h-9 w-9 items-center justify-center rounded-md bg-muted text-muted-foreground">
                        <AppIcon :name="option.icon" class="h-5 w-5" />
                      </span>
                      <AppIcon v-if="themeMode === option.value" name="statusSuccess" class="h-4 w-4 text-foreground" />
                    </div>
                    <div>
                      <div class="text-sm font-semibold">{{ option.label }}</div>
                      <div class="mt-1 text-xs text-muted-foreground">{{ option.description }}</div>
                    </div>
                  </button>
                </div>
              </section>

              <section v-if="currentTab === 'content'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>内容与隐私</h3>
                  <p>控制内容展示与过滤偏好。</p>
                </div>

                <div class="settings-panel">
                  <div class="settings-row">
                    <div class="min-w-0">
                      <div class="settings-row-title">显示敏感内容</div>
                      <div class="settings-row-desc">启用后在平台显示标记为敏感的内容。</div>
                    </div>
                    <Switch
                      :checked="!!settings.showNsfw"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
                    />
                  </div>
                  <div class="settings-row">
                    <div class="min-w-0">
                      <div class="settings-row-title">自动模糊封面</div>
                      <div class="settings-row-desc">对敏感内容缩略图应用模糊效果。</div>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
                    />
                  </div>
                </div>
              </section>

              <section v-if="currentTab === 'playback'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>播放行为</h3>
                  <p>管理播放器的默认行为。</p>
                </div>

                <div class="settings-panel">
                  <div v-for="item in playbackItems" :key="item.key" class="settings-row">
                    <div class="min-w-0">
                      <div class="settings-row-title">{{ item.title }}</div>
                      <div class="settings-row-desc">{{ item.desc }}</div>
                    </div>
                    <Switch
                      :checked="!!settings[item.key]"
                      :disabled="userSaving"
                      @update:checked="(value: boolean) => { settings[item.key] = !!value; onUserSettingChange() }"
                    />
                  </div>
                </div>
              </section>

              <section v-if="currentTab === 'security'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>账户安全</h3>
                  <p>修改密码并管理当前账户的登录会话。</p>
                </div>

                <div v-if="securityError" class="settings-alert settings-alert--error">
                  <AppIcon name="warning" class="h-4 w-4" />
                  {{ securityError }}
                </div>
                <div v-if="securitySuccess" class="settings-alert settings-alert--success">
                  <AppIcon name="statusSuccess" class="h-4 w-4" />
                  {{ securitySuccess }}
                </div>

                <div class="settings-panel p-4">
                  <div class="mb-4 flex items-center gap-2 text-sm font-semibold">
                    <AppIcon name="securityAlert" class="h-4 w-4 text-muted-foreground" />
                    修改登录密码
                  </div>
                  <form @submit.prevent="handlePasswordUpdate" class="max-w-md space-y-4">
                    <div v-for="field in passwordFields" :key="field.key" class="space-y-2">
                      <label class="text-xs font-medium text-muted-foreground">{{ field.label }}</label>
                      <Input
                        v-model="securityForm[field.key]"
                        :type="field.type"
                        :placeholder="field.placeholder"
                        :disabled="passwordSubmitting"
                        class="h-9 rounded-md border-border/50 text-sm shadow-none"
                      />
                    </div>
                    <Button type="submit" :disabled="passwordSubmitting" class="h-9 rounded-md px-3">
                      <AppIcon v-if="passwordSubmitting" name="refresh" class="h-4 w-4 animate-spin" />
                      {{ passwordSubmitting ? '更新中' : '更新密码' }}
                    </Button>
                  </form>
                </div>

                <div class="settings-panel">
                  <div class="settings-row">
                    <div class="min-w-0">
                      <div class="settings-row-title">注销其他会话</div>
                      <div class="settings-row-desc">使除当前设备外所有已登录的设备失效。</div>
                    </div>
                    <Button variant="destructive" class="h-9 rounded-md px-3" :disabled="sessionSubmitting" @click="handleRevokeSessions">
                      <AppIcon name="logout" class="h-4 w-4" />
                      撤销会话
                    </Button>
                  </div>
                </div>
              </section>

              <section v-if="currentTab === 'system'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>系统引擎</h3>
                  <p>控制后台核心服务的运行状态。</p>
                </div>

                <div class="settings-panel">
                  <div v-for="item in systemItems" :key="item.key" class="settings-row">
                    <div class="min-w-0">
                      <div class="settings-row-title">{{ item.title }}</div>
                      <div class="settings-row-desc">{{ item.desc }}</div>
                    </div>
                    <Switch
                      :checked="Boolean(systemConfig?.[item.key])"
                      :disabled="systemLoading || systemSaving"
                      @update:checked="(value: boolean) => onSystemToggle(item.key, !!value)"
                    />
                  </div>
                </div>
              </section>

              <section v-if="currentTab === 'server'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>服务器配置</h3>
                  <p>管理与后端接口的连接地址。</p>
                </div>

                <div class="settings-panel p-4">
                  <div class="flex flex-col gap-3 border-b border-border/50 pb-4 sm:flex-row sm:items-center sm:justify-between">
                    <div class="min-w-0 space-y-1">
                      <div class="settings-row-title">当前连接</div>
                      <div class="truncate rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground">
                        {{ currentServerUrl || '未配置' }}
                      </div>
                    </div>
                    <div v-if="serverTestResult !== null" class="inline-flex h-7 items-center rounded-md border px-2 text-xs font-medium" :class="serverTestResult ? 'border-border/50 bg-background text-foreground' : 'border-destructive/20 bg-destructive/10 text-destructive'">
                      {{ serverTestResult ? '连接正常' : '连接失败：' + serverTestMessage }}
                    </div>
                  </div>

                  <div class="mt-4 max-w-xl space-y-3">
                    <label class="text-xs font-medium text-muted-foreground">服务器地址</label>
                    <div class="flex flex-col gap-2 sm:flex-row">
                      <Input
                        v-model="serverForm.url"
                        type="url"
                        placeholder="http://127.0.0.1:8001"
                        :disabled="serverSaving"
                        class="h-9 rounded-md border-border/50 text-sm shadow-none"
                      />
                      <Button variant="outline" class="h-9 rounded-md px-3" :disabled="serverTesting || !serverForm.url.trim()" @click="handleTestServer">
                        <AppIcon v-if="serverTesting" name="refresh" class="h-4 w-4 animate-spin" />
                        {{ serverTesting ? '测试中' : '测试' }}
                      </Button>
                      <Button class="h-9 rounded-md px-3" :disabled="serverSaving || !serverForm.url.trim()" @click="handleSaveServer">
                        <AppIcon v-if="serverSaving" name="refresh" class="h-4 w-4 animate-spin" />
                        {{ serverSaving ? '保存中' : '保存' }}
                      </Button>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </main>
        </div>
      </main>

      <Transition name="toast">
        <div v-if="saveToastVisible" class="fixed bottom-6 right-6 z-50">
          <div :class="[
            'flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg',
            saveToastError ? 'border-destructive/20 bg-background text-destructive' : 'border-border/50 bg-foreground text-background'
          ]">
            <AppIcon v-if="!saveToastError" name="statusSuccess" class="h-4 w-4" />
            <AppIcon v-else name="warning" class="h-4 w-4" />
            {{ saveToastMessage }}
          </div>
        </div>
      </Transition>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { revokeUserSessions, updateUserPassword } from '@/api'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import {
  DEFAULT_SETTINGS_TAB,
  SETTINGS_TABS,
  getSettingsTabByRouteName,
  type SettingsTabItem,
  type SettingsTabKey,
} from '@/constants/sidebar'
import type { AppIconName } from '@/icons/app-icons'
import { useAppTheme } from '@/composables/useAppTheme'
import { useServerConfig } from '@/composables/useServerConfig'
import type { AppThemeMode } from '@/lib/theme'
import { Logger } from '@/utils/logger'
import { useSystemConfig } from '../composables/useSystemConfig'
import { useUserSettings } from '../composables/useUserSettings'

const route = useRoute()
const router = useRouter()

const tabs = SETTINGS_TABS
const currentTab = computed<SettingsTabKey>(() => {
  return getSettingsTabByRouteName(route.name)?.key || DEFAULT_SETTINGS_TAB
})
const activeTab = computed<SettingsTabItem>(() => tabs.find(tab => tab.key === currentTab.value) as SettingsTabItem)
const tabDescriptions: Record<SettingsTabKey, string> = {
  appearance: '调整界面主题和显示偏好。',
  content: '控制内容展示与隐私偏好。',
  playback: '管理播放器默认行为。',
  security: '修改密码并管理登录会话。',
  system: '控制后台服务运行状态。',
  server: '配置后端接口连接地址。',
}
const activeTabDescription = computed(() => tabDescriptions[currentTab.value])

const themeOptions: Array<{ value: AppThemeMode; label: string; description: string; icon: AppIconName }> = [
  { value: 'light', label: '浅色', description: '明亮主题', icon: 'themeLight' },
  { value: 'dark', label: '深色', description: '护眼模式', icon: 'themeDark' },
  { value: 'system', label: '系统', description: '自动跟随', icon: 'themeSystem' },
]
const playbackItems = [
  { key: 'autoplay', title: '自动播放', desc: '进入详情页时自动开始播放。' },
  { key: 'autoplayNext', title: '自动续播', desc: '当前播放完成后自动播放下一项。' },
  { key: 'loop', title: '循环播放', desc: '播放完成后重新开始当前项目。' },
]
const systemItems = [
  { key: 'enable_scheduler', title: '任务调度器', desc: '管理所有定时采集与同步任务的引擎。' },
  { key: 'enable_worker', title: '异步工作流', desc: '处理高并发数据抓取与分发的执行单元。' },
]
const passwordFields = [
  { key: 'currentPassword', label: '当前密码', placeholder: '输入旧密码', type: 'password' },
  { key: 'newPassword', label: '新密码', placeholder: '至少 8 位字符', type: 'password' },
  { key: 'confirmPassword', label: '确认新密码', placeholder: '再次输入新密码', type: 'password' },
]

const { themeMode, setThemeMode } = useAppTheme()

// User settings
const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings()

// System config
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig()
const systemSaving = ref(false)
const pageLoading = ref(true)
const passwordSubmitting = ref(false)
const sessionSubmitting = ref(false)
const securityError = ref('')
const securitySuccess = ref('')
interface SecurityForm {
  currentPassword: string
  newPassword: string
  confirmPassword: string
  [key: string]: string
}

const securityForm = ref<SecurityForm>({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

// Server config
const { serverUrl: currentServerUrl, setServerUrl, testServerConnection, initServerConfig } = useServerConfig()
const serverForm = ref({ url: '' })
const serverSaving = ref(false)
const serverTesting = ref(false)
const serverTestResult = ref<boolean | null>(null)
const serverTestMessage = ref('')

// Save toast
const saveToastVisible = ref(false)
const saveToastMessage = ref('')
const saveToastError = ref(false)
const hasUnsavedChanges = ref(false)

let saveToastTimer: ReturnType<typeof setTimeout> | null = null

const showSaveToast = (message: string, isError = false) => {
  if (saveToastTimer) clearTimeout(saveToastTimer)
  saveToastMessage.value = message
  saveToastError.value = isError
  saveToastVisible.value = true
  saveToastTimer = setTimeout(() => { saveToastVisible.value = false }, 3000)
}

const resetSecurityFeedback = () => {
  securityError.value = ''
  securitySuccess.value = ''
}

const navigateToTab = (path: string) => {
  if (route.path !== path) router.push(path)
}

onMounted(async () => {
  pageLoading.value = true
  await initServerConfig()
  await Promise.all([
    loadUserSettings(),
    loadSystemConfig().then(result => {
      if (result.error) Logger.error('Failed to load system config', result.error)
    }),
  ])
  serverForm.value.url = currentServerUrl.value || ''
  pageLoading.value = false
})

const onUserSettingChange = async () => {
  userSaving.value = true
  hasUnsavedChanges.value = true
  try {
    await saveUserSettings()
    showSaveToast('设置已更新')
  } catch (err) {
    Logger.warn('[Settings] Failed to save user settings', err)
    showSaveToast('更新失败', true)
  } finally {
    userSaving.value = false
    hasUnsavedChanges.value = false
  }
}

const onSystemToggle = async (key: string, val: boolean) => {
  systemSaving.value = true
  const result = await updateSystemConfig({ [key]: val })
  if (result.error) {
    showSaveToast('更新失败', true)
  } else {
    showSaveToast('系统配置已更新')
  }
  systemSaving.value = false
}

const handleTestServer = async () => {
  if (!serverForm.value.url.trim()) return
  serverTesting.value = true
  serverTestResult.value = null
  try {
    const result = await testServerConnection(serverForm.value.url)
    serverTestResult.value = result.ok
    serverTestMessage.value = result.message
  } catch (err) {
    Logger.warn('[Settings] Server test failed', err)
    serverTestResult.value = false
    serverTestMessage.value = '无法连接'
  } finally {
    serverTesting.value = false
  }
}

const handleSaveServer = async () => {
  if (!serverForm.value.url.trim()) return
  serverSaving.value = true
  try {
    const ok = await setServerUrl(serverForm.value.url)
    if (!ok) {
      showSaveToast('无效的服务器地址', true)
      return
    }
    showSaveToast('服务器已更新')
    serverForm.value.url = currentServerUrl.value || ''
  } catch (err) {
    Logger.warn('[Settings] Failed to save server', err)
    showSaveToast('保存失败', true)
  } finally {
    serverSaving.value = false
  }
}

const handlePasswordUpdate = async () => {
  resetSecurityFeedback()
  if (!securityForm.value.currentPassword || !securityForm.value.newPassword || !securityForm.value.confirmPassword) {
    securityError.value = '请填写完整信息'
    return
  }
  if (securityForm.value.newPassword.length < 8) {
    securityError.value = '新密码至少 8 位'
    return
  }
  if (securityForm.value.newPassword !== securityForm.value.confirmPassword) {
    securityError.value = '两次输入不一致'
    return
  }
  passwordSubmitting.value = true
  try {
    const result = await updateUserPassword({
      current_password: securityForm.value.currentPassword,
      new_password: securityForm.value.newPassword,
    })
    if (result.error) {
      securityError.value = result.error.message || '更新失败'
      return
    }
    securitySuccess.value = '密码更新成功'
    securityForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
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
      securityError.value = '撤销失败'
      return
    }
    securitySuccess.value = '其他会话已撤销'
  } finally {
    sessionSubmitting.value = false
  }
}
</script>

<style scoped>
.settings-section-title {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.settings-section-title h3 {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.settings-section-title p {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.settings-panel {
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.5rem;
  background: hsl(var(--background));
}

.settings-panel > .settings-row + .settings-row {
  border-top: 1px solid hsl(var(--border) / 0.5);
}

.settings-row {
  display: flex;
  min-height: 4.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
}

.settings-row-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.settings-row-desc {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.settings-alert {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.5rem;
  border: 1px solid hsl(var(--border) / 0.5);
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.settings-alert--error {
  border-color: hsl(var(--destructive) / 0.2);
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

.settings-alert--success {
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--foreground));
}

.custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }

.toast-enter-active, .toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateY(0.75rem);
}
</style>

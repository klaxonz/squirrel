<template>
  <AppPageShell class="settings-page" variant="compact" :fill="false">
    <AppToolbarFrame bordered sticky>
      <div class="settings-toolbar">
        <AppSectionNav
          class="app-section-nav--optical"
          :model-value="currentTab"
          :options="tabNavOptions"
          aria-label="设置分区"
          @change="handleTabChange"
        />

        <span v-if="hasUnsavedChanges" class="settings-save-state">
          <AppIcon name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
          正在保存
        </span>
      </div>
    </AppToolbarFrame>

    <main class="app-page-content settings-content">
      <div v-if="pageLoading" class="settings-loading">
        <AppSkeleton height="1.5rem" width="8rem" rounded="var(--radius-md)" shimmer />
        <AppSkeleton height="5rem" rounded="var(--radius-lg)" shimmer />
        <AppSkeleton height="5rem" rounded="var(--radius-lg)" shimmer />
      </div>

      <div v-else-if="pageLoadError" class="app-page-empty app-page-empty--compact">
        <AppEmptyState
          variant="error"
          title="设置加载失败"
          :copy="pageLoadError"
        >
          <template #actions>
            <Button size="sm" @click="reloadSettingsPage">重试</Button>
          </template>
        </AppEmptyState>
      </div>

      <div v-else class="settings-sections">
        <section v-if="currentTab === 'appearance'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>主题</h2>
          </div>

          <div class="app-settings-panel">
            <div class="app-settings-row settings-theme-row">
              <div class="app-settings-row__title">颜色模式</div>
              <AppSegmentedControl
                :model-value="themeMode"
                :options="themeOptions"
                aria-label="界面主题"
                class="settings-theme-control"
                @update:model-value="handleThemeModeChange"
              >
                <template #option="{ option }">
                  <AppIcon v-if="option.icon" :name="option.icon" class="h-4 w-4" />
                  <span>{{ option.label }}</span>
                </template>
              </AppSegmentedControl>
            </div>
          </div>
        </section>

        <section v-if="currentTab === 'content'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>内容过滤</h2>
          </div>

          <div class="app-settings-panel">
            <div class="app-settings-row">
              <div class="app-settings-row__title">显示敏感内容</div>
              <Switch
                :model-value="Boolean(settings.showNsfw)"
                :disabled="userSaving"
                aria-label="显示敏感内容"
                @update:model-value="updateUserSetting('showNsfw', $event)"
              />
            </div>
            <div class="app-settings-row">
              <div class="app-settings-row__title">模糊敏感封面</div>
              <Switch
                :model-value="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                :disabled="systemLoading || systemSaving"
                aria-label="模糊敏感封面"
                @update:model-value="onSystemToggle('blur_nsfw_thumbnails', $event)"
              />
            </div>
          </div>
        </section>

        <section v-if="currentTab === 'playback'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>连续播放</h2>
          </div>

          <div class="app-settings-panel">
            <div v-for="item in playbackItems" :key="item.key" class="app-settings-row">
              <div class="app-settings-row__title">{{ item.title }}</div>
              <Switch
                :model-value="Boolean(settings[item.key])"
                :disabled="userSaving"
                :aria-label="item.title"
                @update:model-value="updateUserSetting(item.key, $event)"
              />
            </div>
          </div>
        </section>

        <SecuritySettings v-if="currentTab === 'security'" />

        <section v-if="currentTab === 'system'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>后台服务</h2>
          </div>

          <div class="app-settings-panel">
            <div v-for="item in systemItems" :key="item.key" class="app-settings-row">
              <div class="app-settings-row__title">{{ item.title }}</div>
              <Switch
                :model-value="Boolean(systemConfig?.[item.key])"
                :disabled="systemLoading || systemSaving"
                :aria-label="item.title"
                @update:model-value="onSystemToggle(item.key, $event)"
              />
            </div>
          </div>
        </section>

        <section v-if="currentTab === 'server'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>后端连接</h2>
          </div>

          <div class="app-settings-panel">
            <div class="app-settings-row settings-server-summary">
              <div class="app-settings-row__copy">
                <div class="app-settings-row__title">当前服务器</div>
                <code class="settings-server-url">{{ currentServerUrl || '尚未配置' }}</code>
              </div>
            </div>

            <form class="settings-server-form" @submit.prevent="handleSwitchServer">
              <label for="settings-server-url" class="settings-field-label">更换服务器</label>
              <div class="settings-server-form__controls">
                <Input
                  id="settings-server-url"
                  v-model="serverForm.url"
                  type="url"
                  placeholder="http://127.0.0.1:8001"
                  :disabled="serverSaving || serverTesting"
                />
                <Button
                  type="button"
                  variant="outline"
                  :loading="serverTesting"
                  :disabled="serverSaving || !serverForm.url.trim()"
                  @click="handleTestServer"
                >
                  测试连接
                </Button>
                <Button
                  type="submit"
                  :loading="serverSaving"
                  :disabled="serverTesting || !canSwitchServer"
                >
                  切换服务器
                </Button>
              </div>

              <div class="settings-server-form__meta">
                <p class="settings-server-notice">
                  切换后应用会重新载入；目标服务器没有有效会话时，将返回登录页。
                </p>
                <span
                  v-if="serverTestResult !== null"
                  class="settings-connection-state"
                  :class="serverTestResult ? 'is-success' : 'is-error'"
                >
                  <AppIcon :name="serverTestResult ? 'statusSuccess' : 'warning'" class="h-3.5 w-3.5" />
                  {{ serverTestResult ? '目标服务器可用' : serverTestMessage }}
                </span>
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Switch } from '@/shared/ui/switch'
import SecuritySettings from '@/features/settings/components/SecuritySettings.vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import {
  SETTINGS_TABS,
  getSettingsTabByRouteName,
  type SettingsTabItem,
  type SettingsTabKey,
} from '@/shared/constants/sidebar'
import type { AppIconName } from '@/shared/icons/app-icons'
import { useThemeStore } from '@/shared/stores/theme'
import { useServerConfig } from '@/shared/composables/useServerConfig'
import { useToast } from '@/shared/components/toast/useToast'
import type { AppThemeMode } from '@/shared/lib/theme'
import { Logger } from '@/shared/lib/logger'
import { useSystemConfig } from '@/shared/composables/useSystemConfig'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import { useServerConfigForm } from '@/features/settings/composables/useServerConfigForm'

const route = useRoute()
const router = useRouter()

const tabs = SETTINGS_TABS
const tabNavOptions = tabs.map((tab) => ({
  value: tab.key,
  label: tab.label,
  badge: tab.badge,
}))

const activeTab = computed<SettingsTabItem>(() => {
  const tab = getSettingsTabByRouteName(route.name)
  if (!tab) {
    throw new Error(`[Settings] Unknown settings route: ${String(route.name)}`)
  }
  return tab
})
const currentTab = computed<SettingsTabKey>(() => activeTab.value.key)

const themeOptions: Array<{
  value: AppThemeMode
  label: string
  icon: AppIconName
}> = [
  { value: 'light', label: '浅色', icon: 'themeLight' },
  { value: 'dark', label: '深色', icon: 'themeDark' },
  { value: 'system', label: '跟随系统', icon: 'themeSystem' },
]

const playbackItems = [
  { key: 'autoplay', title: '自动播放' },
  { key: 'autoplayNext', title: '自动续播' },
  { key: 'loop', title: '单项循环' },
] as const

const systemItems = [
  { key: 'enable_scheduler', title: '任务调度器' },
  { key: 'enable_worker', title: '异步工作进程' },
] as const

const themeStore = useThemeStore()
const { themeMode } = storeToRefs(themeStore)
const { setThemeMode } = themeStore

const {
  settings,
  loading: userSaving,
  error: userSettingsError,
  loadUserSettings,
  saveUserSettings,
} = useUserSettings()
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig()
const systemSaving = ref(false)
const pageLoading = ref(true)
const systemLoadError = ref('')
const pageLoadError = computed(() => {
  if (userSettingsError.value) {
    return errorMessage(userSettingsError.value, '无法加载用户设置，请检查后端连接后重试。')
  }
  if (systemLoadError.value) return systemLoadError.value
  return ''
})

const { serverUrl: currentServerUrl, initServerConfig } = useServerConfig()
const {
  serverForm,
  serverSaving,
  serverTesting,
  serverTestResult,
  serverTestMessage,
  canSwitchServer,
  handleTestServer,
  handleSwitchServer,
} = useServerConfigForm()

const toast = useToast()
const hasUnsavedChanges = ref(false)

const navigateToTab = (path: string) => {
  if (route.path !== path) {
    void router.push(path)
  }
}

const handleTabChange = (value: string | number) => {
  const tab = tabs.find((item) => item.key === value)
  if (!tab) {
    throw new Error(`[Settings] Unknown settings tab: ${String(value)}`)
  }
  navigateToTab(tab.path)
}

const handleThemeModeChange = (value: string | number) => {
  setThemeMode(value as AppThemeMode)
}

const updateUserSetting = (
  key: 'showNsfw' | (typeof playbackItems)[number]['key'],
  value: boolean,
) => {
  settings.value[key] = value
  void saveUserSettingChanges()
}

const reloadSettingsPage = async () => {
  pageLoading.value = true
  systemLoadError.value = ''
  try {
    await initServerConfig()
    await Promise.all([
      loadUserSettings(true),
      loadSystemConfig().catch((error) => {
        Logger.error('Failed to load system config', error)
        systemLoadError.value = errorMessage(error, '无法加载系统配置，请检查后端连接后重试。')
      }),
    ])
    serverForm.value.url = currentServerUrl.value || ''
  } finally {
    pageLoading.value = false
  }
}

onMounted(() => {
  void reloadSettingsPage()
})

const saveUserSettingChanges = async () => {
  userSaving.value = true
  hasUnsavedChanges.value = true
  try {
    await saveUserSettings()
    toast.success('设置已更新')
  } catch (error) {
    Logger.warn('[Settings] Failed to save user settings', error)
    toast.error('更新失败')
  } finally {
    userSaving.value = false
    hasUnsavedChanges.value = false
  }
}

const onSystemToggle = async (key: string, value: boolean) => {
  systemSaving.value = true
  try {
    await updateSystemConfig({ [key]: value })
    toast.success('系统配置已更新')
  } catch (error) {
    Logger.warn('[Settings] Failed to update system config', error)
    toast.error('更新失败')
  } finally {
    systemSaving.value = false
  }
}
</script>

<style scoped>
.settings-page {
  --settings-content-width: 72rem;
}

.settings-toolbar {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.settings-save-state {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-1);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
}

.settings-content {
  display: flex;
  flex-direction: column;
  padding-top: var(--space-5);
}

.settings-loading,
.settings-sections {
  display: flex;
  width: min(100%, var(--settings-content-width));
  flex-direction: column;
  gap: var(--space-6);
}

.settings-theme-row {
  min-height: 5rem;
}

.settings-theme-control {
  width: min(100%, 24rem);
}

.settings-theme-control :deep(.app-segmented-control__item) {
  min-width: 0;
  flex: 1 1 0;
  gap: var(--space-2);
  justify-content: center;
}

.settings-server-summary {
  min-height: 5rem;
}

.settings-server-url {
  display: block;
  margin-top: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-family: var(--font-mono);
  font-size: 0.75rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.settings-connection-state {
  display: inline-flex;
  min-height: 1.75rem;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-1);
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: var(--radius-md);
  padding: 0 var(--space-2);
  font-size: 0.75rem;
  font-weight: 600;
}

.settings-connection-state.is-success {
  border-color: hsl(var(--success) / 0.28);
  background: hsl(var(--success) / 0.08);
  color: hsl(var(--success));
}

.settings-connection-state.is-error {
  border-color: hsl(var(--destructive) / 0.28);
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

.settings-server-form {
  border-top: 1px solid var(--app-hairline);
  padding: var(--space-4);
}

.settings-field-label {
  display: block;
  margin-bottom: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
}

.settings-server-form__controls {
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) auto auto;
  gap: var(--space-2);
}

.settings-server-form__meta {
  display: flex;
  min-height: 1.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.settings-server-notice {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .settings-theme-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .settings-theme-control {
    width: 100%;
  }

  .settings-server-form__controls {
    grid-template-columns: 1fr auto;
  }

  .settings-server-form__controls > :first-child {
    grid-column: 1 / -1;
  }

  .settings-server-form__meta {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

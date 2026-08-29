<template>
  <!-- Desktop settings workbench — left nav + dense content, not top tabs. -->
  <AppPageShell class="settings-page" variant="compact" surface="operate" width="form" fill>
    <AppTwoColumnLayout preset="settings" sidebar-always>
      <template #sidebar>
      <div class="settings-nav" aria-label="设置分区">
        <header class="settings-nav__header">
          <div class="settings-nav__title">设置</div>
          <span v-if="hasUnsavedChanges" class="settings-save-state">
            <AppIcon name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
            保存中
          </span>
        </header>
        <nav class="settings-nav__list">
          <button
            v-for="tab in settingsTabs"
            :key="tab.key"
            type="button"
            class="settings-nav__item"
            :class="{ 'is-active': currentTab === tab.key }"
            :aria-current="currentTab === tab.key ? 'page' : undefined"
            @click="handleTabChange(tab.key)"
          >
            <AppIcon :name="tab.icon" class="h-4 w-4 shrink-0" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>
      </div>
      </template>

      <main class="settings-content custom-scrollbar">
      <div v-if="pageLoading" class="settings-loading">
        <AppSkeleton height="1.5rem" width="8rem" rounded="var(--radius-md)" shimmer />
        <AppSkeleton height="3.25rem" rounded="var(--radius-lg)" shimmer />
        <AppSkeleton height="3.25rem" rounded="var(--radius-lg)" shimmer />
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

      <!-- Each section carries its own title + description (the tab label and
           description would only duplicate them), so sections lead directly. -->
      <div v-else class="settings-sections">
        <section v-if="currentTab === 'appearance'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>外观</h2>
            <p>控制桌面端配色与对比；改动立即生效，无需保存。</p>
          </div>

          <div class="app-settings-panel">
            <div class="app-settings-row settings-theme-row">
              <div class="app-settings-row__copy">
                <div class="app-settings-row__title">颜色模式</div>
                <div class="app-settings-row__desc">浅色、深色或跟随操作系统主题。</div>
              </div>
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
            <h2>内容</h2>
            <p>过滤与封面展示策略，影响订阅列表与首页推荐。</p>
          </div>

          <div class="app-settings-panel">
            <div
              class="app-settings-row app-settings-row--toggle"
              :class="{ 'is-disabled': userSaving }"
              @click="toggleUserSettingRow('showNsfw', Boolean(settings.showNsfw), userSaving)"
            >
              <div class="app-settings-row__copy">
                <div class="app-settings-row__title">显示敏感内容</div>
                <div class="app-settings-row__desc">关闭后隐藏标记为敏感的条目（账号级）。</div>
              </div>
              <Switch
                :model-value="Boolean(settings.showNsfw)"
                :disabled="userSaving"
                aria-label="显示敏感内容"
                @click.stop
                @update:model-value="updateUserSetting('showNsfw', $event)"
              />
            </div>
            <div
              class="app-settings-row app-settings-row--toggle"
              :class="{ 'is-disabled': systemLoading || systemSaving }"
              @click="toggleSystemSettingRow('blur_nsfw_thumbnails', Boolean(systemConfig?.blur_nsfw_thumbnails), systemLoading || systemSaving)"
            >
              <div class="app-settings-row__copy">
                <div class="app-settings-row__title">模糊敏感封面</div>
                <div class="app-settings-row__desc">仍可打开条目，但缩略图默认模糊（系统级）。</div>
              </div>
              <Switch
                :model-value="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                :disabled="systemLoading || systemSaving"
                aria-label="模糊敏感封面"
                @click.stop
                @update:model-value="onSystemToggle('blur_nsfw_thumbnails', $event)"
              />
            </div>
          </div>
        </section>

        <section v-if="currentTab === 'playback'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>播放</h2>
            <p>控制视频打开后的自动播放与续播行为。</p>
          </div>

          <div class="app-settings-panel">
            <div
              v-for="item in playbackItems"
              :key="item.key"
              class="app-settings-row app-settings-row--toggle"
              :class="{ 'is-disabled': userSaving }"
              @click="toggleUserSettingRow(item.key, Boolean(settings[item.key]), userSaving)"
            >
              <div class="app-settings-row__copy">
                <div class="app-settings-row__title">{{ item.title }}</div>
                <div class="app-settings-row__desc">{{ item.description }}</div>
              </div>
              <Switch
                :model-value="Boolean(settings[item.key])"
                :disabled="userSaving"
                :aria-label="item.title"
                @click.stop
                @update:model-value="updateUserSetting(item.key, $event)"
              />
            </div>
          </div>
        </section>

        <SecuritySettings v-if="currentTab === 'security'" />

        <section v-if="currentTab === 'system'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>系统服务</h2>
            <p>后台调度与异步任务进程；关闭后定时同步会暂停。</p>
          </div>

          <div class="app-settings-panel">
            <div
              v-for="item in systemItems"
              :key="item.key"
              class="app-settings-row app-settings-row--toggle"
              :class="{ 'is-disabled': systemLoading || systemSaving }"
              @click="toggleSystemSettingRow(item.key, Boolean(systemConfig?.[item.key]), systemLoading || systemSaving)"
            >
              <div class="app-settings-row__copy">
                <div class="app-settings-row__title">{{ item.title }}</div>
                <div class="app-settings-row__desc">{{ item.description }}</div>
              </div>
              <Switch
                :model-value="Boolean(systemConfig?.[item.key])"
                :disabled="systemLoading || systemSaving"
                :aria-label="item.title"
                @click.stop
                @update:model-value="onSystemToggle(item.key, $event)"
              />
            </div>
          </div>
        </section>

        <section v-if="currentTab === 'server'" class="app-settings-section">
          <div class="app-settings-section-title">
            <h2>后端连接</h2>
            <p>桌面端当前连接的 API 地址；切换后会重新载入会话。</p>
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
                <Input fluid
                  id="settings-server-url"
                  v-model="serverForm.url"
                  type="url"
                  placeholder="http://127.0.0.1:8001"
                  :disabled="serverSaving || serverTesting"
                />
                <Button
                  type="button"
                  variant="secondary" outlined
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
    </AppTwoColumnLayout>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Skeleton as AppSkeleton } from '@/shared/ui/skeleton'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Switch } from '@/shared/ui/switch'
import SecuritySettings from '@/features/settings/components/SecuritySettings.vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import {
  DEFAULT_SETTINGS_TAB,
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
import { nextSettingsToggleValue } from '@/features/settings/lib/settingsToggleRow'

const route = useRoute()
const router = useRouter()

const defaultSettingsTab = SETTINGS_TABS.find((tab) => tab.key === DEFAULT_SETTINGS_TAB) ?? SETTINGS_TABS[0]
const settingsTabs = SETTINGS_TABS

/**
 * Resolve the active settings tab from the leaf route name.
 *
 * Must NOT throw when `route.name` leaves the settings tree. App.vue uses
 * `<Transition mode="out-in">`; during leave the component is still mounted
 * while `useRoute()` already reflects the destination (e.g. HomeView /
 * Profile). A throw here aborts the leave→enter handshake and leaves
 * `.app-layout__stage` empty until a full reload — the blank-page bug after
 * clicking another sidebar item from 设置.
 */
const activeTab = computed<SettingsTabItem>(() => {
  return getSettingsTabByRouteName(route.name) ?? defaultSettingsTab
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
  { key: 'autoplay', title: '自动播放', description: '打开视频页后立即尝试起播。' },
  { key: 'autoplayNext', title: '自动续播', description: '当前视频结束后播放下一集/相关项。' },
  { key: 'loop', title: '单项循环', description: '仅循环当前视频，忽略续播队列。' },
] as const

const systemItems = [
  { key: 'enable_scheduler', title: '任务调度器', description: '定时同步订阅与计划任务入口。' },
  { key: 'enable_worker', title: '异步工作进程', description: '处理导入、抽帧等后台作业。' },
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

const handleTabChange = (value: SettingsTabKey) => {
  const tab = SETTINGS_TABS.find((item) => item.key === value)
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

const toggleUserSettingRow = (
  key: 'showNsfw' | (typeof playbackItems)[number]['key'],
  current: boolean,
  disabled: boolean,
) => {
  const next = nextSettingsToggleValue(current, disabled)
  if (next === null) return
  updateUserSetting(key, next)
}

const toggleSystemSettingRow = (
  key: string,
  current: boolean,
  disabled: boolean,
) => {
  const next = nextSettingsToggleValue(current, disabled)
  if (next === null) return
  void onSystemToggle(key, next)
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
  --settings-nav-width: 12rem;
  --settings-content-width: var(--app-content-form-max);
}

.settings-nav {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: var(--space-3);
  border-right: 1px solid hsl(var(--border));
  padding: var(--space-5) var(--space-3);
  background: transparent;
  height: 100%;
}

.settings-nav__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 0 var(--space-2);
}

.settings-nav__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-sans);
  font-size: var(--app-text-xl);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.settings-nav__list {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 2px;
  overflow: auto;
}

.settings-nav__item {
  display: flex;
  width: 100%;
  min-height: 2.25rem;
  align-items: center;
  gap: 0.55rem;
  border: 0;
  border-radius: var(--radius-md);
  padding: 0 0.75rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.settings-nav__item:hover {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground));
}

.settings-nav__item.is-active {
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground));
  font-weight: 650;
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.04);
}

.settings-nav__item:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px hsl(var(--ring) / 0.55);
}

.settings-save-state {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-1);
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 600;
}

.settings-content {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: auto;
  padding: var(--space-6) var(--space-6) var(--space-8);
  background: hsl(var(--card));
}

.settings-loading,
.settings-sections {
  display: flex;
  width: min(100%, var(--settings-content-width));
  flex: 0 0 auto;
  flex-direction: column;
  align-self: center;
  gap: var(--space-6);
}

/* Multi-line settings rows stay scannable (title + description + control). */
.settings-theme-row,
.settings-sections :deep(.app-settings-row) {
  min-height: 3.5rem;
  align-items: flex-start;
  padding-top: 0.875rem;
  padding-bottom: 0.875rem;
}

.settings-sections :deep(.app-settings-row__copy) {
  min-width: 0;
  flex: 1 1 auto;
}

.settings-sections :deep(.app-settings-row > :not(.app-settings-row__copy)) {
  flex: 0 0 auto;
  margin-top: 0.125rem;
}

.settings-theme-control {
  width: min(100%, 22rem);
}

.settings-theme-control :deep(.app-segmented-control__item) {
  min-width: 0;
  flex: 1 1 0;
  gap: var(--space-2);
  justify-content: center;
}

.settings-server-summary {
  min-height: 3.25rem;
}

.settings-server-url {
  display: block;
  margin-top: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-family: var(--font-mono);
  font-size: var(--app-text-sm);
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
  font-size: var(--app-text-sm);
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
  font-size: var(--app-text-sm);
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
  font-size: var(--app-text-sm);
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

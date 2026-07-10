<template>
  <AppPageShell variant="compact" fill>
    <div class="settings-page">
      <div class="settings-control-bar">
        <nav class="settings-view-nav" aria-label="设置分区">
          <Button
            v-for="tab in tabs"
            :key="tab.key"
            unstyled
            type="button"
            class="settings-view-nav__item"
            :class="{ 'is-active': currentTab === tab.key }"
            :aria-current="currentTab === tab.key ? 'page' : undefined"
            @click="navigateToTab(tab.path)"
          >
            <AppIcon :name="tab.icon" class="h-4 w-4" />
            <span>{{ tab.label }}</span>
            <span v-if="tab.badge" class="settings-view-nav__badge app-mono">{{ tab.badge }}</span>
          </Button>
        </nav>

        <span v-if="hasUnsavedChanges" class="settings-save-state">
          <AppIcon name="loadingSpinner" class="h-3.5 w-3.5 animate-spin" />
          正在保存
        </span>
      </div>

      <main class="settings-workspace">
        <div class="settings-scroll custom-scrollbar">
          <div class="settings-content">
            <header class="settings-page-header">
              <h1>{{ activeTab.label }}</h1>
              <p>{{ activeTabDescription }}</p>
            </header>

            <div v-if="pageLoading" class="settings-loading">
              <AppSkeleton height="1.5rem" width="8rem" rounded="var(--radius-md)" shimmer />
              <AppSkeleton height="5rem" rounded="var(--radius-lg)" shimmer />
              <AppSkeleton height="5rem" rounded="var(--radius-lg)" shimmer />
            </div>

            <div v-else class="settings-sections">
              <section v-if="currentTab === 'appearance'" class="app-settings-section">
                <div class="app-settings-section-title">
                  <h2>颜色模式</h2>
                  <p>选择界面的明暗模式，系统模式会跟随操作系统设置。</p>
                </div>

                <div class="app-settings-panel">
                  <div class="app-settings-row settings-theme-row">
                    <div class="app-settings-row__copy">
                      <div class="app-settings-row__title">应用主题</div>
                      <div class="app-settings-row__desc">当前模式会立即应用到整个应用。</div>
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
                  <h2>内容过滤</h2>
                  <p>控制敏感内容是否显示，以及封面在列表中的呈现方式。</p>
                </div>

                <div class="app-settings-panel">
                  <div class="app-settings-row">
                    <div class="app-settings-row__copy">
                      <div class="app-settings-row__title">显示敏感内容</div>
                      <div class="app-settings-row__desc">显示平台中标记为敏感的内容。</div>
                    </div>
                    <Switch
                      :model-value="Boolean(settings.showNsfw)"
                      :disabled="userSaving"
                      aria-label="显示敏感内容"
                      @update:model-value="updateUserSetting('showNsfw', $event)"
                    />
                  </div>
                  <div class="app-settings-row">
                    <div class="app-settings-row__copy">
                      <div class="app-settings-row__title">模糊敏感封面</div>
                      <div class="app-settings-row__desc">在列表和网格中模糊敏感内容的缩略图。</div>
                    </div>
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
                  <p>设置打开媒体和播放结束后的默认行为。</p>
                </div>

                <div class="app-settings-panel">
                  <div v-for="item in playbackItems" :key="item.key" class="app-settings-row">
                    <div class="app-settings-row__copy">
                      <div class="app-settings-row__title">{{ item.title }}</div>
                      <div class="app-settings-row__desc">{{ item.description }}</div>
                    </div>
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
                  <p>控制任务调度与异步处理服务是否随应用运行。</p>
                </div>

                <div class="app-settings-panel">
                  <div v-for="item in systemItems" :key="item.key" class="app-settings-row">
                    <div class="app-settings-row__copy">
                      <div class="app-settings-row__title">{{ item.title }}</div>
                      <div class="app-settings-row__desc">{{ item.description }}</div>
                    </div>
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
                  <p>配置应用访问后端服务时使用的基础地址。</p>
                </div>

                <div class="app-settings-panel">
                  <div class="app-settings-row settings-server-summary">
                    <div class="app-settings-row__copy">
                      <div class="app-settings-row__title">当前地址</div>
                      <code class="settings-server-url">{{ currentServerUrl || '尚未配置' }}</code>
                    </div>
                    <span
                      v-if="serverTestResult !== null"
                      class="settings-connection-state"
                      :class="serverTestResult ? 'is-success' : 'is-error'"
                    >
                      <AppIcon :name="serverTestResult ? 'statusSuccess' : 'warning'" class="h-3.5 w-3.5" />
                      {{ serverTestResult ? '连接正常' : serverTestMessage }}
                    </span>
                  </div>

                  <form class="settings-server-form" @submit.prevent="handleSaveServer">
                    <label for="settings-server-url" class="settings-field-label">服务器地址</label>
                    <div class="settings-server-form__controls">
                      <Input
                        id="settings-server-url"
                        v-model="serverForm.url"
                        type="url"
                        placeholder="http://127.0.0.1:8001"
                        :disabled="serverSaving"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        :loading="serverTesting"
                        :disabled="!serverForm.url.trim()"
                        @click="handleTestServer"
                      >
                        测试连接
                      </Button>
                      <Button
                        type="submit"
                        :loading="serverSaving"
                        :disabled="!serverForm.url.trim()"
                      >
                        保存地址
                      </Button>
                    </div>
                  </form>
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Switch } from '@/shared/ui/switch'
import SecuritySettings from '@/features/settings/components/SecuritySettings.vue'
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

const activeTab = computed<SettingsTabItem>(() => {
  const tab = getSettingsTabByRouteName(route.name)
  if (!tab) {
    throw new Error(`[Settings] Unknown settings route: ${String(route.name)}`)
  }
  return tab
})
const currentTab = computed<SettingsTabKey>(() => activeTab.value.key)

const tabDescriptions: Record<SettingsTabKey, string> = {
  appearance: '调整主题模式与界面呈现。',
  content: '管理敏感内容的展示方式。',
  playback: '设置媒体播放的默认行为。',
  security: '更新登录凭据并管理账户会话。',
  system: '控制应用后台服务的运行状态。',
  server: '配置应用连接的后端服务地址。',
}
const activeTabDescription = computed(() => tabDescriptions[currentTab.value])

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
  { key: 'autoplay', title: '自动播放', description: '打开媒体详情后自动开始播放。' },
  { key: 'autoplayNext', title: '自动续播', description: '当前内容结束后继续播放下一项。' },
  { key: 'loop', title: '单项循环', description: '播放结束后重新播放当前内容。' },
] as const

const systemItems = [
  { key: 'enable_scheduler', title: '任务调度器', description: '执行定时采集、刷新和同步任务。' },
  { key: 'enable_worker', title: '异步工作进程', description: '处理抓取、转码和数据分发等后台工作。' },
] as const

const themeStore = useThemeStore()
const { themeMode } = storeToRefs(themeStore)
const { setThemeMode } = themeStore

const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings()
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig()
const systemSaving = ref(false)
const pageLoading = ref(true)

const { serverUrl: currentServerUrl, initServerConfig } = useServerConfig()
const {
  serverForm,
  serverSaving,
  serverTesting,
  serverTestResult,
  serverTestMessage,
  handleTestServer,
  handleSaveServer,
} = useServerConfigForm()

const toast = useToast()
const hasUnsavedChanges = ref(false)

const navigateToTab = (path: string) => {
  if (route.path !== path) {
    void router.push(path)
  }
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

onMounted(async () => {
  pageLoading.value = true
  await initServerConfig()
  await Promise.all([
    loadUserSettings(),
    loadSystemConfig().catch((error) => Logger.error('Failed to load system config', error)),
  ])
  serverForm.value.url = currentServerUrl.value || ''
  pageLoading.value = false
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
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.settings-control-bar {
  display: flex;
  min-height: 3.5rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 var(--space-5);
}

.settings-view-nav {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.25rem;
  overflow-x: auto;
}

.settings-view-nav__item {
  display: inline-flex;
  height: 3.5rem;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.45rem;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 550;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.settings-view-nav__item:hover,
.settings-view-nav__item:focus-visible {
  background: hsl(var(--muted) / 0.28);
  color: hsl(var(--foreground));
  outline: none;
}

.settings-view-nav__item.is-active {
  color: hsl(var(--foreground));
  box-shadow: inset 0 -2px 0 hsl(var(--foreground) / 0.58);
}

.settings-view-nav__badge {
  color: hsl(var(--muted-foreground) / 0.76);
  font-size: 0.5625rem;
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

.settings-workspace,
.settings-scroll {
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
}

.settings-workspace {
  display: flex;
  overflow: hidden;
}

.settings-scroll {
  overflow-y: auto;
}

.settings-content {
  width: min(100%, 72rem);
  margin: 0 auto;
  padding: var(--space-6) var(--space-6) var(--app-content-padding-bottom);
}

.settings-page-header {
  border-bottom: 1px solid var(--app-hairline);
  padding-bottom: var(--space-5);
}

.settings-page-header h1 {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1.5rem;
  font-weight: 650;
  line-height: 1.2;
}

.settings-page-header p {
  max-width: 40rem;
  margin: var(--space-2) 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  line-height: 1.5;
}

.settings-loading,
.settings-sections {
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
  padding-top: var(--space-6);
}

.settings-content :deep(.app-settings-section) {
  gap: var(--space-3);
}

.settings-content :deep(.app-settings-panel) {
  overflow: visible;
  border: 0;
  border-top: 1px solid var(--app-hairline);
  border-bottom: 1px solid var(--app-hairline);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.settings-content :deep(.app-settings-panel > .app-settings-row + .app-settings-row) {
  border-top-color: var(--app-hairline);
}

.settings-content :deep(.app-settings-row) {
  min-height: 4.5rem;
  padding: var(--space-4) var(--space-1);
}

.settings-content :deep(.app-settings-row__copy) {
  min-width: 0;
  max-width: 40rem;
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
  padding: var(--space-4) var(--space-1) var(--space-1);
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

@media (max-width: 1100px) {
  .settings-control-bar,
  .settings-content {
    padding-inline: var(--space-4);
  }

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
}

@media (prefers-reduced-motion: reduce) {
  .settings-view-nav__item {
    transition: none;
  }
}
</style>

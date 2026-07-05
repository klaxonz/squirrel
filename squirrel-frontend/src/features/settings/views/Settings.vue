<template>
  <AppPageShell variant="compact">
    <AppTwoColumnLayout>
      <template #sidebar>
        <div class="settings-sidebar-header">
          <div class="min-w-0">
            <h1 class="app-h3 truncate">设置</h1>
            <p>{{ activeTab.label }}</p>
          </div>
          <span v-if="hasUnsavedChanges" class="settings-save-state">
            保存中
          </span>
        </div>

        <nav class="settings-sidebar-nav custom-scrollbar">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            @click="navigateToTab(tab.path)"
            class="settings-nav-item"
            :class="{ 'settings-nav-item--active': currentTab === tab.key }"
          >
            <AppIcon :name="tab.icon" class="h-4 w-4" />
            <span class="min-w-0 flex-1 truncate">{{ tab.label }}</span>
            <span v-if="tab.badge" class="settings-nav-badge">{{ tab.badge }}</span>
          </button>
        </nav>
      </template>

      <template #header>
        <div class="settings-header-copy">
          <h2 class="app-h2 truncate">{{ activeTab.label }}</h2>
          <p>{{ activeTabDescription }}</p>
        </div>

        <div class="settings-header-actions">
          <span v-if="hasUnsavedChanges" class="settings-save-state settings-save-state--header">
            保存中
          </span>
        </div>
      </template>

        <div class="settings-scroll custom-scrollbar">
          <main class="settings-main">
            <div v-if="pageLoading" class="space-y-3">
              <AppSkeleton height="3rem" rounded="var(--radius-lg)" shimmer />
              <AppSkeleton height="12rem" rounded="var(--radius-lg)" shimmer />
              <AppSkeleton height="9rem" rounded="var(--radius-lg)" shimmer />
            </div>

            <div v-else class="space-y-6">
              <section v-if="currentTab === 'appearance'" class="space-y-4">
                <div class="settings-section-title">
                  <h3>界面外观</h3>
                  <p>选择偏好的视觉主题。</p>
                </div>

                <div class="settings-theme-grid">
                  <button
                    v-for="option in themeOptions"
                    :key="option.value"
                    @click="setThemeMode(option.value)"
                    class="settings-theme-option"
                    :class="{ 'settings-theme-option--active': themeMode === option.value }"
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
                      :model-value="!!settings.showNsfw"
                      :disabled="userSaving"
                      @update:model-value="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
                    />
                  </div>
                  <div class="settings-row">
                    <div class="min-w-0">
                      <div class="settings-row-title">自动模糊封面</div>
                      <div class="settings-row-desc">对敏感内容缩略图应用模糊效果。</div>
                    </div>
                    <Switch
                      :model-value="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                      :disabled="systemLoading || systemSaving"
                      @update:model-value="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
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
                      :model-value="!!settings[item.key]"
                      :disabled="userSaving"
                      @update:model-value="(value: boolean) => { settings[item.key] = !!value; onUserSettingChange() }"
                    />
                  </div>
                </div>
              </section>

              <SecuritySettings v-if="currentTab === 'security'" />

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
                      :model-value="Boolean(systemConfig?.[item.key])"
                      :disabled="systemLoading || systemSaving"
                      @update:model-value="(value: boolean) => onSystemToggle(item.key, !!value)"
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
                      <Button variant="outline" class="h-9 rounded-md px-3" :loading="serverTesting" :disabled="!serverForm.url.trim()" @click="handleTestServer">
                        {{ serverTesting ? '测试中' : '测试' }}
                      </Button>
                      <Button class="h-9 rounded-md px-3" :loading="serverSaving" :disabled="!serverForm.url.trim()" @click="handleSaveServer">
                        {{ serverSaving ? '保存中' : '保存' }}
                      </Button>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </main>
        </div>
    </AppTwoColumnLayout>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { Button } from '@/shared/ui/button'
import { Switch } from '@/shared/ui/switch'
import { Input } from '@/shared/ui/input'
import SecuritySettings from '@/features/settings/components/SecuritySettings.vue'
import {
  DEFAULT_SETTINGS_TAB,
  SETTINGS_TABS,
  getSettingsTabByRouteName,
  type SettingsTabItem,
  type SettingsTabKey,
} from '@/shared/constants/sidebar'
import type { AppIconName } from '@/shared/icons/app-icons'
import { storeToRefs } from 'pinia'
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

// ponytail: useThemeStore replaces the deleted useAppTheme composable.
// storeToRefs keeps themeMode reactive for the v-model bindings; the action
// setThemeMode is destructured directly (Pinia actions don't need wrapping).
const themeStore = useThemeStore()
const { themeMode } = storeToRefs(themeStore)
const { setThemeMode } = themeStore

// User settings
const { settings, loading: userSaving, loadUserSettings, saveUserSettings } = useUserSettings()

// System config
const { config: systemConfig, loading: systemLoading, loadSystemConfig, updateSystemConfig } = useSystemConfig()
const systemSaving = ref(false)
const pageLoading = ref(true)

// ponytail: server-url config form (test-connection → result → save flow,
// with loading guards + error mapping) lives in useServerConfigForm. The host
// still owns the onMounted initServerConfig() call (it coordinates parallel
// loads) and re-syncs serverForm.url from the canonical value after init.
// initServerConfig + currentServerUrl come from the shared useServerConfig
// singleton (module-level state), so the form composable and this view agree.
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

// Save toast
const toast = useToast()
const hasUnsavedChanges = ref(false)

const navigateToTab = (path: string) => {
  if (route.path !== path) router.push(path)
}

onMounted(async () => {
  pageLoading.value = true
  await initServerConfig()
  await Promise.all([
    loadUserSettings(),
    loadSystemConfig().catch((err) => Logger.error('Failed to load system config', err)),
  ])
  serverForm.value.url = currentServerUrl.value || ''
  pageLoading.value = false
})

const onUserSettingChange = async () => {
  userSaving.value = true
  hasUnsavedChanges.value = true
  try {
    await saveUserSettings()
    toast.success('设置已更新')
  } catch (err) {
    Logger.warn('[Settings] Failed to save user settings', err)
    toast.error('更新失败')
  } finally {
    userSaving.value = false
    hasUnsavedChanges.value = false
  }
}

const onSystemToggle = async (key: string, val: boolean) => {
  systemSaving.value = true
  try {
    await updateSystemConfig({ [key]: val })
    toast.success('系统配置已更新')
  } catch (err) {
    Logger.warn('[Settings] Failed to update system config', err)
    toast.error('更新失败')
  } finally {
    systemSaving.value = false
  }
}

</script>

<style scoped>
.settings-sidebar-header {
  display: flex;
  min-height: 4.25rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.48);
  padding: 0 1rem;
}

.settings-sidebar-header p,
.settings-header-copy p {
  margin-top: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.35;
}

.settings-save-state {
  display: inline-flex;
  height: 1.75rem;
  align-items: center;
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.45);
  padding: 0 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.settings-save-state--header {
  display: none;
}

.settings-sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.625rem;
}

.settings-nav-item {
  display: flex;
  width: 100%;
  height: 2.25rem;
  align-items: center;
  gap: 0.5rem;
  border: 0;
  border-radius: 0.4375rem;
  background: transparent;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground));
  text-align: left;
  font-size: 0.875rem;
  font-weight: 600;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.settings-nav-item + .settings-nav-item {
  margin-top: 0.125rem;
}

.settings-nav-item:hover,
.settings-nav-item--active {
  background: hsl(var(--accent) / 0.62);
  color: hsl(var(--foreground));
}

.settings-nav-item--active :deep(svg) {
  color: hsl(var(--primary));
}

.settings-nav-badge {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.settings-header-copy {
  min-width: 0;
}

.settings-header-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: 0.5rem;
}

.settings-scroll {
  flex: 1;
  overflow-y: auto;
}

.settings-main {
  width: 100%;
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem;
}

.settings-section-title {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.settings-section-title h3 {
  font-family: var(--app-heading-font);
  font-size: 1rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  letter-spacing: -0.01em;
}

.settings-section-title p {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.settings-panel {
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0.625rem;
  background: hsl(var(--card) / 0.58);
}

.settings-panel > .settings-row + .settings-row {
  border-top: 1px solid hsl(var(--border) / 0.5);
}

.settings-row {
  display: flex;
  min-height: 4.125rem;
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

.settings-theme-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.settings-theme-option {
  position: relative;
  display: flex;
  min-height: 7rem;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid hsl(var(--border) / 0.55);
  border-radius: 0.625rem;
  background: hsl(var(--card) / 0.58);
  padding: 1rem;
  color: hsl(var(--foreground));
  text-align: left;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.settings-theme-option:hover,
.settings-theme-option--active {
  border-color: hsl(var(--primary) / 0.32);
  background: hsl(var(--accent) / 0.45);
}

@media (min-width: 640px) {
  .settings-save-state--header {
    display: inline-flex;
  }
}

@media (prefers-reduced-motion: reduce) {
  .settings-nav-item,
  .settings-theme-option {
    transition: none;
  }
}
</style>

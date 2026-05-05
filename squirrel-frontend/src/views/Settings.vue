<template>
  <AppPageShell class="settings-page bg-slate-50/50">
    <!-- Header Area -->
    <div class="w-full bg-white">
      <div class="w-full max-w-[1400px] mx-auto px-6 py-10">
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h1 class="text-xl font-semibold text-slate-900 tracking-tight">系统设置</h1>
            <p class="text-sm text-slate-500">管理个人偏好、安全选项与系统核心配置</p>
          </div>
          
          <Transition name="status-pop">
            <div v-if="hasUnsavedChanges" class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-100 text-[11px] font-bold text-amber-600 uppercase tracking-wider">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
              未保存的更改
            </div>
          </Transition>
        </div>

        <!-- Tab Navigation (Linear Style) -->
        <div class="flex items-center gap-1 mt-10 p-1 bg-slate-100/50 rounded-lg w-fit">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            @click="navigateToTab(tab.path)"
            :class="[
              'px-4 py-1.5 rounded-md text-xs font-semibold transition-all whitespace-nowrap flex items-center gap-2',
              currentTab === tab.key 
                ? 'bg-white text-slate-900 shadow-sm' 
                : 'text-slate-500 hover:text-slate-700'
            ]"
          >
            <AppIcon :name="tab.icon" class="w-3.5 h-3.5" />
            {{ tab.label }}
            <span v-if="tab.badge" class="px-1.5 py-0.5 rounded-full bg-slate-100 text-[10px]">{{ tab.badge }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="w-full max-w-[1400px] mx-auto px-6 py-8">
      <!-- Skeleton Loading -->
      <div v-if="pageLoading" class="space-y-8">
        <div v-for="i in 2" :key="i" class="space-y-4">
          <div class="h-4 w-24 bg-slate-200 animate-pulse rounded"></div>
          <div class="h-48 w-full bg-white rounded-xl border border-slate-200 animate-pulse"></div>
        </div>
      </div>

      <div v-else class="max-w-3xl space-y-12">
        <!-- Appearance Tab -->
        <div v-if="currentTab === 'appearance'" class="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div class="space-y-1">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">界面外观</h2>
            <p class="text-xs text-slate-500">选择您偏好的视觉主题</p>
          </div>

          <div class="grid grid-cols-3 gap-4">
            <button
              v-for="option in themeOptions"
              :key="option.value"
              @click="setThemeMode(option.value)"
              :class="[
                'group relative flex flex-col items-center gap-4 p-6 rounded-xl border transition-all text-center',
                themeMode === option.value 
                  ? 'bg-white border-slate-900 shadow-md' 
                  : 'bg-white border-slate-200 hover:border-slate-300'
              ]"
            >
              <div :class="[
                'w-12 h-12 rounded-lg flex items-center justify-center transition-colors',
                themeMode === option.value ? 'bg-slate-900 text-white' : 'bg-slate-50 text-slate-400 group-hover:bg-slate-100'
              ]">
                <AppIcon :name="option.icon" class="w-6 h-6" />
              </div>
              <div class="space-y-1">
                <div class="text-sm font-bold text-slate-900">{{ option.label }}</div>
                <div class="text-[11px] text-slate-400">{{ option.description }}</div>
              </div>
              <div v-if="themeMode === option.value" class="absolute top-3 right-3 text-slate-900">
                <AppIcon name="statusSuccess" class="w-4 h-4" />
              </div>
            </button>
          </div>
        </div>

        <!-- Content Tab -->
        <div v-if="currentTab === 'content'" class="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div class="space-y-1">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">内容与隐私</h2>
            <p class="text-xs text-slate-500">控制内容展示与过滤偏好</p>
          </div>

          <div class="bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.05),0_0_0_1px_rgba(0,0,0,0.05)] divide-y divide-slate-100">
            <div class="flex items-center justify-between p-6">
              <div class="space-y-1">
                <div class="text-sm font-semibold text-slate-900">显示敏感内容</div>
                <div class="text-xs text-slate-500">启用后在平台显示标记为敏感的内容</div>
              </div>
              <Switch
                :checked="!!settings.showNsfw"
                :disabled="userSaving"
                @update:checked="(value: boolean) => { settings.showNsfw = !!value; onUserSettingChange() }"
              />
            </div>
            <div class="flex items-center justify-between p-6">
              <div class="space-y-1">
                <div class="text-sm font-semibold text-slate-900">自动模糊封面</div>
                <div class="text-xs text-slate-500">对敏感内容缩略图应用模糊效果</div>
              </div>
              <Switch
                :checked="Boolean(systemConfig?.blur_nsfw_thumbnails)"
                :disabled="systemLoading || systemSaving"
                @update:checked="(value: boolean) => onSystemToggle('blur_nsfw_thumbnails', !!value)"
              />
            </div>
          </div>
        </div>

        <!-- Playback Tab -->
        <div v-if="currentTab === 'playback'" class="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div class="space-y-1">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">播放行为</h2>
            <p class="text-xs text-slate-500">管理媒体播放器的默认行为</p>
          </div>

          <div class="bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.05),0_0_0_1px_rgba(0,0,0,0.05)] divide-y divide-slate-100">
            <div v-for="item in [
              { key: 'autoplay', title: '自动播放', desc: '进入详情页时自动开始播放' },
              { key: 'autoplayNext', title: '自动续播', desc: '当前播放完成后自动播放下一项' },
              { key: 'loop', title: '循环播放', desc: '播放完成后重新开始当前项目' }
            ]" :key="item.key" class="flex items-center justify-between p-6">
              <div class="space-y-1">
                <div class="text-sm font-semibold text-slate-900">{{ item.title }}</div>
                <div class="text-xs text-slate-500">{{ item.desc }}</div>
              </div>
              <Switch
                :checked="!!(settings as any)[item.key]"
                :disabled="userSaving"
                @update:checked="(value: boolean) => { (settings as any)[item.key] = !!value; onUserSettingChange() }"
              />
            </div>
          </div>
        </div>

        <!-- Security Tab -->
        <div v-if="currentTab === 'security'" class="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div class="space-y-6">
            <div class="space-y-1">
              <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">账户安全</h2>
              <p class="text-xs text-slate-500">保护您的账户免受未经授权的访问</p>
            </div>

            <div v-if="securityError" class="p-4 rounded-lg bg-rose-50 border border-rose-100 flex items-center gap-3 text-sm text-rose-700">
              <AppIcon name="warning" class="w-4 h-4" /> {{ securityError }}
            </div>
            <div v-if="securitySuccess" class="p-4 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center gap-3 text-sm text-emerald-700">
              <AppIcon name="statusSuccess" class="w-4 h-4" /> {{ securitySuccess }}
            </div>

            <div class="bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.05),0_0_0_1px_rgba(0,0,0,0.05)] p-8">
              <h3 class="text-sm font-bold text-slate-900 mb-6 flex items-center gap-2">
                <AppIcon name="securityAlert" class="w-4 h-4 text-slate-400" /> 修改登录密码
              </h3>
              <form @submit.prevent="handlePasswordUpdate" class="space-y-6 max-w-md">
                <div v-for="field in [
                  { key: 'currentPassword', label: '当前密码', placeholder: '输入旧密码', type: 'password' },
                  { key: 'newPassword', label: '新密码', placeholder: '至少 8 位字符', type: 'password' },
                  { key: 'confirmPassword', label: '确认新密码', placeholder: '再次输入新密码', type: 'password' }
                ]" :key="field.key" class="space-y-2">
                  <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{{ field.label }}</label>
                  <Input
                    v-model="(securityForm as any)[field.key]"
                    :type="field.type"
                    :placeholder="field.placeholder"
                    :disabled="passwordSubmitting"
                    class="h-10 bg-white border-slate-200 rounded-lg text-sm focus-visible:ring-slate-200 shadow-none"
                  />
                </div>
                <Button type="submit" :disabled="passwordSubmitting" class="bg-slate-900 text-white hover:bg-slate-800">
                  {{ passwordSubmitting ? '正在更新...' : '更新密码' }}
                </Button>
              </form>
            </div>
          </div>

          <div class="bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.05),0_0_0_1px_rgba(0,0,0,0.05)] p-8 flex items-center justify-between">
            <div class="space-y-1">
              <div class="text-sm font-semibold text-slate-900">注销其他会话</div>
              <div class="text-xs text-slate-500">使除当前设备外所有已登录的设备失效</div>
            </div>
            <Button variant="outline" :disabled="sessionSubmitting" @click="handleRevokeSessions" class="border-rose-200 text-rose-600 hover:bg-rose-50 hover:border-rose-300 transition-colors">
              <AppIcon name="logout" class="w-4 h-4 mr-2" /> 撤销所有会话
            </Button>
          </div>
        </div>

        <!-- System Tab -->
        <div v-if="currentTab === 'system'" class="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div class="space-y-1">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">系统引擎</h2>
            <p class="text-xs text-slate-500">控制后台核心服务的运行状态</p>
          </div>

          <div class="bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.05),0_0_0_1px_rgba(0,0,0,0.05)] divide-y divide-slate-100">
            <div v-for="item in [
              { key: 'enable_scheduler', title: '任务调度器', desc: '管理所有定时采集与同步任务的引擎' },
              { key: 'enable_worker', title: '异步工作流', desc: '处理高并发数据抓取与分发的执行单元' }
            ]" :key="item.key" class="flex items-center justify-between p-6">
              <div class="space-y-1">
                <div class="text-sm font-semibold text-slate-900">{{ item.title }}</div>
                <div class="text-xs text-slate-500">{{ item.desc }}</div>
              </div>
              <Switch
                :checked="Boolean((systemConfig as any)?.[item.key])"
                :disabled="systemLoading || systemSaving"
                @update:checked="(value: boolean) => onSystemToggle(item.key, !!value)"
              />
            </div>
          </div>
        </div>

        <!-- Server Tab -->
        <div v-if="currentTab === 'server'" class="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div class="space-y-1">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider">服务器配置</h2>
            <p class="text-xs text-slate-500">管理与后端接口的连接地址</p>
          </div>

          <div class="bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.05),0_0_0_1px_rgba(0,0,0,0.05)] p-8 space-y-8">
            <div class="flex items-center justify-between">
              <div class="space-y-1">
                <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">当前连接</div>
                <div class="text-sm font-mono font-bold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-md border border-blue-100">
                  {{ currentServerUrl || '未配置' }}
                </div>
              </div>
              <div v-if="serverTestResult !== null" :class="[
                'text-[11px] font-bold px-3 py-1.5 rounded-full border',
                serverTestResult ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-rose-50 border-rose-100 text-rose-600'
              ]">
                {{ serverTestResult ? '连接正常' : '连接失败: ' + serverTestMessage }}
              </div>
            </div>

            <div class="space-y-4 max-w-md">
              <div class="space-y-2">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">修改服务器地址</label>
                <div class="flex gap-2">
                  <Input
                    v-model="serverForm.url"
                    type="url"
                    placeholder="http://127.0.0.1:8001"
                    :disabled="serverSaving"
                    class="h-10 bg-white border-slate-200 rounded-lg text-sm focus-visible:ring-slate-200 shadow-none"
                  />
                  <Button variant="outline" :disabled="serverTesting || !serverForm.url.trim()" @click="handleTestServer" class="h-10 border-slate-200">
                    <AppIcon v-if="serverTesting" name="refresh" class="w-4 h-4 animate-spin" />
                    <span v-else>测试</span>
                  </Button>
                </div>
              </div>
              <Button :disabled="serverSaving || !serverForm.url.trim()" @click="handleSaveServer" class="bg-slate-900 text-white hover:bg-slate-800">
                {{ serverSaving ? '正在保存...' : '保存并重连' }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Feedback Toast -->
    <Transition name="toast">
      <div v-if="saveToastVisible" class="fixed bottom-6 right-6 z-50">
        <div :class="[
          'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border text-sm font-medium transition-all',
          saveToastError ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-slate-900 border-slate-800 text-white'
        ]">
          <AppIcon v-if="!saveToastError" name="statusSuccess" class="h-4 w-4 text-emerald-400" />
          <AppIcon v-else name="warning" class="h-4 w-4 text-rose-400" />
          {{ saveToastMessage }}
        </div>
      </div>
    </Transition>
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

const themeOptions: Array<{ value: AppThemeMode; label: string; description: string; icon: AppIconName }> = [
  { value: 'light', label: '浅色', description: '明亮主题', icon: 'themeLight' },
  { value: 'dark', label: '深色', description: '护眼模式', icon: 'themeDark' },
  { value: 'system', label: '系统', description: '自动跟随', icon: 'themeSystem' },
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
const securityForm = ref({
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
  } catch {
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
  } catch {
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
.settings-page {
  min-height: 100vh;
  scrollbar-gutter: stable;
}

.status-pop-enter-active, .status-pop-leave-active {
  transition: all 0.3s ease;
}
.status-pop-enter-from, .status-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.toast-enter-active, .toast-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}
</style>

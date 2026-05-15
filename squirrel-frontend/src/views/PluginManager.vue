<template>
  <AppPageShell variant="compact">
    <div class="flex h-full overflow-hidden bg-background text-foreground">
      <aside class="hidden w-72 shrink-0 flex-col border-r border-border/50 bg-background lg:flex">
        <div class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4">
          <div class="min-w-0">
            <h1 class="truncate text-sm font-semibold">插件</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ pluginSummary.total }} 个已安装</p>
          </div>
          <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md" :disabled="reloading || loading" @click="handleReload">
            <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': reloading }" />
          </Button>
        </div>

        <div class="grid shrink-0 grid-cols-2 gap-2 border-b border-border/50 p-3">
          <div class="rounded-md border border-border/50 p-2">
            <div class="text-xs text-muted-foreground">运行</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ pluginSummary.running }}</div>
          </div>
          <div class="rounded-md border border-border/50 p-2">
            <div class="text-xs text-muted-foreground">需关注</div>
            <div class="mt-1 text-lg font-semibold tabular-nums">{{ pluginSummary.attention }}</div>
          </div>
          <div class="col-span-2 rounded-md border border-border/50 p-2">
            <div class="flex items-center justify-between">
              <span class="text-xs text-muted-foreground">网络连通</span>
              <span class="text-sm font-semibold tabular-nums">{{ connectivitySummary.accessible }}/{{ connectivitySummary.total }}</span>
            </div>
            <p v-if="lastTestedAt" class="mt-1 text-xs text-muted-foreground">最近检测 {{ formatTime(lastTestedAt) }}</p>
          </div>
        </div>

        <div class="space-y-4 border-b border-border/50 p-3">
          <div class="space-y-2">
            <div class="text-xs font-medium text-muted-foreground">插件包</div>
            <Button as-child variant="outline" class="h-9 w-full justify-start rounded-md">
              <label class="cursor-pointer">
                <input type="file" accept=".zip" class="hidden" @change="handleFileChange" />
                <AppIcon name="upload" class="h-4 w-4" />
                <span class="truncate">{{ selectedFile ? selectedFile.name : '选择插件包' }}</span>
              </label>
            </Button>
            <Button v-if="selectedFile" class="h-9 w-full rounded-md" :disabled="installing" @click="handleInstall">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': installing }" />
              安装插件
            </Button>
          </div>

          <div class="space-y-2">
            <div class="text-xs font-medium text-muted-foreground">登录凭据</div>
            <Button as-child variant="outline" class="h-9 w-full justify-start rounded-md">
              <label class="cursor-pointer">
                <input type="file" accept=".txt,.json" class="hidden" @change="handleCookiesFileChange" />
                <AppIcon name="cookie" class="h-4 w-4" />
                <span class="truncate">{{ cookiesFileName || '选择凭据文件' }}</span>
              </label>
            </Button>
            <Button v-if="selectedCookiesFile" class="h-9 w-full rounded-md" :disabled="importingCookies" @click="handleImportAllCookies">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': importingCookies }" />
              导入凭据
            </Button>
          </div>
        </div>

        <div class="space-y-2 p-3">
          <Button variant="outline" class="h-9 w-full justify-start rounded-md" :disabled="testingAll" @click="handleTestAll">
            <AppIcon name="sync" class="h-4 w-4" :class="{ 'animate-spin': testingAll }" />
            测试全部
          </Button>
        </div>
      </aside>

      <main class="flex min-w-0 flex-1 flex-col bg-background">
        <header class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4 lg:px-6">
          <div class="min-w-0">
            <h2 class="truncate text-base font-semibold">插件管理</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ pluginSummary.total }} 个插件 · {{ pluginSummary.running }} 个运行</p>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <div class="relative hidden w-80 md:block">
              <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="searchQuery"
                placeholder="搜索插件、站点或描述"
                class="h-9 w-full rounded-md border-border/50 pl-9 pr-8 text-sm shadow-none"
              />
              <button
                v-if="searchQuery"
                @click="searchQuery = ''"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70 transition-colors hover:text-foreground"
              >
                <AppIcon name="close" class="h-4 w-4" />
              </button>
            </div>
            <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md lg:hidden" :disabled="reloading || loading" @click="handleReload">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': reloading }" />
            </Button>
          </div>
        </header>

        <div class="shrink-0 space-y-2 border-b border-border/50 p-3 md:hidden">
          <div class="relative">
            <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="searchQuery"
              placeholder="搜索插件、站点或描述"
              class="h-9 w-full rounded-md border-border/50 pl-9 pr-8 text-sm shadow-none"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70 transition-colors hover:text-foreground"
            >
              <AppIcon name="close" class="h-4 w-4" />
            </button>
          </div>
          <div class="flex gap-2">
            <Button as-child variant="outline" class="h-9 flex-1 justify-start rounded-md">
              <label class="cursor-pointer">
                <input type="file" accept=".zip" class="hidden" @change="handleFileChange" />
                <AppIcon name="upload" class="h-4 w-4" />
                <span class="truncate">{{ selectedFile ? selectedFile.name : '插件包' }}</span>
              </label>
            </Button>
            <Button as-child variant="outline" class="h-9 flex-1 justify-start rounded-md">
              <label class="cursor-pointer">
                <input type="file" accept=".txt,.json" class="hidden" @change="handleCookiesFileChange" />
                <AppIcon name="cookie" class="h-4 w-4" />
                <span class="truncate">{{ cookiesFileName || '登录凭据' }}</span>
              </label>
            </Button>
          </div>
          <div v-if="selectedFile || selectedCookiesFile" class="flex gap-2">
            <Button v-if="selectedFile" class="h-9 flex-1 rounded-md" :disabled="installing" @click="handleInstall">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': installing }" />
              安装
            </Button>
            <Button v-if="selectedCookiesFile" class="h-9 flex-1 rounded-md" :disabled="importingCookies" @click="handleImportAllCookies">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': importingCookies }" />
              导入
            </Button>
            <Button variant="outline" class="h-9 rounded-md" :disabled="testingAll" @click="handleTestAll">
              <AppIcon name="sync" class="h-4 w-4" :class="{ 'animate-spin': testingAll }" />
            </Button>
          </div>
          <Button v-else variant="outline" class="h-9 w-full rounded-md" :disabled="testingAll" @click="handleTestAll">
            <AppIcon name="sync" class="h-4 w-4" :class="{ 'animate-spin': testingAll }" />
            测试全部
          </Button>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <div class="mx-auto w-full max-w-[1400px] p-4 lg:p-6">
            <div class="overflow-x-auto rounded-lg border border-border/50">
              <div class="plugin-grid min-w-[980px] border-b border-border/50 bg-muted/20 px-4 py-3 text-xs font-medium text-muted-foreground">
                <div>插件</div>
                <div>状态</div>
                <div>能力</div>
                <div>网络</div>
                <div>登录</div>
                <div class="text-right">操作</div>
              </div>

              <div v-if="isInitialLoading" class="min-w-[980px] space-y-2 p-4">
                <div v-for="i in 5" :key="i" class="h-16 animate-pulse rounded-lg bg-accent/30" />
              </div>

              <div v-else-if="!displayPlugins.length" class="flex min-h-[20rem] flex-col items-center justify-center text-center">
                <AppIcon name="cube" class="h-9 w-9 text-muted-foreground/30" />
                <h2 class="mt-4 text-sm font-semibold">{{ searchQuery ? '没有匹配的插件' : '暂无插件' }}</h2>
                <p class="mt-1 text-sm text-muted-foreground">{{ searchQuery ? '更换搜索关键词后再试。' : '导入插件包后会显示在这里。' }}</p>
              </div>

              <div v-else class="min-w-[980px] divide-y divide-border/50">
                <div
                  v-for="plugin in displayPlugins"
                  :key="plugin.plugin_id"
                  class="plugin-grid group items-center px-4 py-3 transition-colors hover:bg-accent/30"
                >
                  <div class="flex min-w-0 items-center gap-3">
                    <SiteIcon
                      v-if="plugin.primarySite"
                      :icon-url="plugin.primarySite.icon_url"
                      :label="plugin.primarySite.site_name || plugin.display_name"
                      size="md"
                      class="rounded-md border border-border/50"
                    />
                    <div v-else class="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-border/50 bg-muted text-muted-foreground">
                      <AppIcon name="cube" class="h-5 w-5" />
                    </div>
                    <div class="min-w-0">
                      <h3 class="truncate text-sm font-semibold text-foreground">{{ plugin.display_name }}</h3>
                      <p v-if="plugin.description" class="mt-1 line-clamp-1 text-xs text-muted-foreground">{{ plugin.description }}</p>
                    </div>
                  </div>

                  <div>
                    <span class="inline-flex h-7 items-center rounded-md border px-2 text-xs font-medium" :class="getPluginStatusClass(plugin)">
                      {{ getPluginStatusText(plugin) }}
                    </span>
                  </div>

                  <div class="flex min-w-0 flex-wrap gap-1">
                    <span
                      v-for="cap in plugin.capabilities.slice(0, 3)"
                      :key="cap.name"
                      class="rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
                      :title="cap.name"
                    >
                      {{ getCapabilityLabel(cap.name) }}
                    </span>
                    <span v-if="plugin.capabilities.length > 3" class="text-xs text-muted-foreground">
                      +{{ plugin.capabilities.length - 3 }}
                    </span>
                  </div>

                  <div class="text-sm text-muted-foreground">
                    <span v-if="plugin.siteTesting" class="inline-flex items-center gap-1">
                      <AppIcon name="refresh" class="h-3.5 w-3.5 animate-spin" />
                      检测中
                    </span>
                    <span v-else>{{ getNetworkText(plugin) }}</span>
                  </div>

                  <div class="text-sm text-muted-foreground">
                    <span v-if="plugin.siteLoginTesting" class="inline-flex items-center gap-1">
                      <AppIcon name="refresh" class="h-3.5 w-3.5 animate-spin" />
                      检测中
                    </span>
                    <span v-else>{{ getLoginText(plugin) }}</span>
                  </div>

                  <div class="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-md text-muted-foreground"
                      :disabled="actioning === plugin.plugin_id"
                      :title="plugin.enabled ? '停用插件' : '启用插件'"
                      @click="plugin.enabled ? handleDisable(plugin) : handleEnable(plugin)"
                    >
                      <AppIcon v-if="plugin.enabled" name="pause" class="h-4 w-4" />
                      <AppIcon v-else name="play" class="h-4 w-4 fill-current" />
                    </Button>
                    <Button
                      v-if="plugin.siteName"
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-md text-muted-foreground"
                      :disabled="plugin.siteTesting"
                      title="连通性测试"
                      @click="handleTestSingleBySite(plugin.siteName)"
                    >
                      <AppIcon name="bolt" class="h-4 w-4" />
                    </Button>
                    <Button
                      v-if="plugin.siteSupportsLogin"
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-md text-muted-foreground"
                      :disabled="plugin.siteLoginTesting"
                      title="验证登录状态"
                      @click="handleTestLoginBySite(plugin.siteName)"
                    >
                      <AppIcon name="security" class="h-4 w-4" />
                    </Button>
                    <DropdownMenu v-if="isDesktopApp && plugin.siteDesktopLoginSupported">
                      <DropdownMenuTrigger as-child>
                        <Button
                          variant="ghost"
                          size="icon"
                          class="h-8 w-8 rounded-md text-muted-foreground"
                          :disabled="plugin.siteLoginTesting"
                          :title="plugin.siteLoginStatus?.logged_in ? '桌面会话已登录' : '桌面会话'"
                        >
                          <AppIcon
                            :name="plugin.siteLoginStatus?.logged_in ? 'statusSuccess' : 'user'"
                            class="h-4 w-4"
                            :class="{ 'text-emerald-500': plugin.siteLoginStatus?.logged_in }"
                          />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" class="w-44">
                        <DropdownMenuItem @click="handleDesktopSiteLogin(plugin.siteName)">
                          <AppIcon name="user" class="h-4 w-4" />
                          <span>{{ plugin.siteLoginStatus?.logged_in ? '重新登录' : '打开桌面登录' }}</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem @click="handleTestLoginBySite(plugin.siteName)">
                          <AppIcon name="refresh" class="h-4 w-4" />
                          <span>刷新登录状态</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          :disabled="!plugin.siteLoginStatus?.logged_in"
                          class="text-destructive focus:text-destructive"
                          @click="handleClearDesktopSiteSession(plugin.siteName)"
                        >
                          <AppIcon name="logout" class="h-4 w-4" />
                          <span>清除桌面会话</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <Button
                      v-if="plugin.siteName === 'youtube'"
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-md text-muted-foreground"
                      title="授权管理"
                      @click="plugin.siteOAuthStatus === 'authenticated' || plugin.siteOAuthStatus === 'pending' ? handleRevokeYouTubeOAuth() : handleStartYouTubeOAuth()"
                    >
                      <AppIcon v-if="plugin.siteOAuthStatus === 'authenticated'" name="link" class="h-4 w-4" />
                      <AppIcon v-else name="unlink" class="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-md text-muted-foreground"
                      title="站点配置"
                      @click="openSiteEditorByPlugin(plugin)"
                    >
                      <AppIcon name="settingsPanel" class="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 rounded-md text-muted-foreground"
                      title="卸载插件"
                      @click="openUninstallDialog(plugin)"
                    >
                      <AppIcon name="trash" class="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <SiteConfigEditorDialog
        :visible="siteEditorVisible"
        :site="editingSite"
        :catalog="siteCatalog"
        :saving="siteEditorSaving"
        :error-message="siteEditorError"
        @close="closeSiteEditor"
        @save="saveSiteEditor"
      />

      <Transition name="toast">
        <div
          v-if="youtubeOAuthPrompt.visible"
          class="fixed bottom-6 right-6 z-50 w-[min(24rem,calc(100vw-2rem))] rounded-md border border-border/60 bg-background p-4 text-foreground shadow-xl"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2 text-sm font-semibold">
                <AppIcon name="link" class="h-4 w-4" />
                <span>YouTube TV 授权</span>
              </div>
              <p class="mt-1 text-xs text-muted-foreground">在授权页输入此代码</p>
            </div>
            <Button variant="ghost" size="icon" class="h-7 w-7 rounded-md text-muted-foreground" title="关闭" @click="hideYouTubeOAuthPrompt">
              <AppIcon name="close" class="h-4 w-4" />
            </Button>
          </div>

          <div class="mt-3 flex items-center gap-2">
            <div class="min-w-0 flex-1 select-all rounded-md border border-border/50 bg-muted px-3 py-2 font-mono text-lg font-semibold text-foreground">
              {{ youtubeOAuthPrompt.userCode }}
            </div>
            <Button variant="outline" size="icon" class="h-10 w-10 rounded-md" title="复制授权码" @click="copyYouTubeOAuthCode">
              <AppIcon name="clipboard" class="h-4 w-4" />
            </Button>
          </div>

          <div class="mt-3 flex items-center justify-between gap-2">
            <span class="text-xs text-muted-foreground">{{ youtubeOAuthPrompt.copied ? '已复制' : '等待授权完成' }}</span>
            <Button variant="outline" class="h-8 rounded-md text-xs" @click="openExternalUrl(youtubeOAuthPrompt.verificationUrl)">
              <AppIcon name="externalLink" class="h-3.5 w-3.5" />
              打开授权页
            </Button>
          </div>
        </div>
      </Transition>

      <Transition name="toast">
        <div
          v-if="toast.visible"
          class="fixed right-6 z-50"
          :class="youtubeOAuthPrompt.visible ? 'bottom-56' : 'bottom-6'"
        >
          <div
            class="flex items-center gap-2 rounded-md border px-4 py-3 text-sm shadow-lg"
            :class="toast.error ? 'border-destructive/20 bg-background text-destructive' : 'border-border/50 bg-foreground text-background'"
          >
            <AppIcon v-if="toast.error" name="warning" class="h-4 w-4" />
            <AppIcon v-else name="statusSuccess" class="h-4 w-4" />
            <span>{{ toast.message }}</span>
          </div>
        </div>
      </Transition>

      <Dialog v-model:open="showUninstallDialog">
        <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
          <DialogHeader class="border-b border-border/50 p-5 text-left">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-destructive/10 text-destructive">
              <AppIcon name="trash" class="h-5 w-5" />
            </div>
            <DialogTitle class="text-base font-semibold">卸载插件？</DialogTitle>
            <DialogDescription class="text-sm leading-relaxed text-muted-foreground">
              确定要卸载插件 <span class="font-semibold text-foreground">"{{ uninstallTarget?.display_name }}"</span> 吗？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter class="gap-2 bg-muted/30 p-4">
            <Button variant="outline" class="h-9 rounded-md" @click="showUninstallDialog = false">取消</Button>
            <Button variant="destructive" class="h-9 rounded-md" @click="confirmUninstall">确认卸载</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  </AppPageShell>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Logger } from '@/utils/logger'
import { mergeLoginStatusResult, shouldRefreshLoginStatusesAfterCookieImport } from '@/utils/plugin-login-status'
import { useSiteCatalog } from '@/composables/useSites'
import {
  disablePlugin,
  enablePlugin,
  getPlugins,
  getSupportedSites,
  importAllSiteCookies,
  installPlugin,
  getYouTubeOAuthStatus,
  reloadPlugins,
  revokeYouTubeOAuth,
  setupYouTubeOAuth,
  testAllSitesConnectivity,
  testSiteConnectivity,
  testSiteLoginStatus,
  uninstallPlugin,
} from '@/api'

const loading = ref(false)
const installing = ref(false)
const reloading = ref(false)
const plugins = ref([])
const selectedFile = ref(null)
const actioning = ref(null)
const isInitialLoading = computed(() => loading.value && !plugins.value.length)

const testingAll = ref(false)
const supportedSites = ref([])
const connectivityResults = ref([])
const loginStatusResults = ref({})
const loginStatusTesting = ref({})
const lastTestedAt = ref(null)
let ytOAuthPollTimer = null

const { catalog: siteCatalog, loadCatalog, saveCatalog } = useSiteCatalog()

const CACHE_KEY_CONNECTIVITY = 'squirrel_connectivity_results'
const CACHE_KEY_LOGIN_STATUS = 'squirrel_login_status_results'
const CACHE_KEY_LAST_TESTED = 'squirrel_last_tested_at'
const CAPABILITY_LABELS = {
  check_login_status: '登录检测',
  import_subscriptions: '导入订阅',
  resolve_subscription: '解析订阅',
  sync_subscription: '同步订阅',
  extract_video: '视频信息',
  resolve_playback: '播放解析',
  fetch_subtitles: '字幕',
  build_mpd: '流媒体',
  resolve_proxy_config: '代理配置',
  rewrite_proxy_playlist: '代理播放',
}
const DESKTOP_LOGIN_SITES = new Set(['bilibili', 'pornhub', 'youporn'])
const isDesktopApp = computed(() => window.desktopApp?.isDesktop === true)

const clearLoginStatusCache = () => {
  loginStatusResults.value = {}
  try {
    localStorage.removeItem(CACHE_KEY_LOGIN_STATUS)
  } catch (error) {
    Logger.warn('Failed to clear login status cache', error)
  }
}

const saveResultsToCache = () => {
  try {
    if (connectivityResults.value.length > 0) {
      localStorage.setItem(CACHE_KEY_CONNECTIVITY, JSON.stringify(connectivityResults.value))
    }
    if (Object.keys(loginStatusResults.value).length > 0) {
      localStorage.setItem(CACHE_KEY_LOGIN_STATUS, JSON.stringify(loginStatusResults.value))
    }
    const now = new Date().toISOString()
    lastTestedAt.value = now
    localStorage.setItem(CACHE_KEY_LAST_TESTED, now)
  } catch (error) {
    Logger.warn('Failed to save connectivity cache', error)
  }
}

const loadResultsFromCache = () => {
  try {
    const cachedConnectivity = localStorage.getItem(CACHE_KEY_CONNECTIVITY)
    const cachedLoginStatus = localStorage.getItem(CACHE_KEY_LOGIN_STATUS)
    const cachedLastTested = localStorage.getItem(CACHE_KEY_LAST_TESTED)

    if (cachedConnectivity) {
      connectivityResults.value = JSON.parse(cachedConnectivity)
    }
    if (cachedLoginStatus) {
      loginStatusResults.value = JSON.parse(cachedLoginStatus)
    }
    if (cachedLastTested) {
      lastTestedAt.value = cachedLastTested
    }
  } catch (error) {
    Logger.warn('Failed to load connectivity cache', error)
  }
}

const selectedCookiesFile = ref(null)
const cookiesFileName = ref('')
const importingCookies = ref(false)
const toast = ref({ visible: false, message: '', error: false })
const youtubeOAuthPrompt = ref({
  visible: false,
  verificationUrl: '',
  userCode: '',
  copied: false,
  dismissedCode: '',
})
let toastTimer = null
let youtubeOAuthCopyTimer = null

const editingSite = ref(null)
const siteEditorVisible = ref(false)
const siteEditorSaving = ref(false)
const siteEditorError = ref('')
const showUninstallDialog = ref(false)
const uninstallTarget = ref(null)

const siteCatalogMap = computed(() => siteCatalog.value || {})
const searchQuery = ref('')

const showToast = (message, isError = false) => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { visible: true, message, error: isError }
  toastTimer = setTimeout(() => { toast.value.visible = false }, 3000)
}

const showYouTubeOAuthPrompt = ({ verificationUrl = '', userCode = '' } = {}) => {
  const code = String(userCode || '').trim()
  if (!code) {
    hideYouTubeOAuthPrompt()
    return
  }
  if (!youtubeOAuthPrompt.value.visible && youtubeOAuthPrompt.value.dismissedCode === code) {
    return
  }
  youtubeOAuthPrompt.value = {
    visible: true,
    verificationUrl: String(verificationUrl || '').trim(),
    userCode: code,
    copied: false,
    dismissedCode: '',
  }
}

const hideYouTubeOAuthPrompt = () => {
  youtubeOAuthPrompt.value.dismissedCode = youtubeOAuthPrompt.value.userCode
  youtubeOAuthPrompt.value.visible = false
}

const copyYouTubeOAuthCode = async () => {
  const code = String(youtubeOAuthPrompt.value.userCode || '').trim()
  if (!code) return
  await navigator.clipboard.writeText(code)
  youtubeOAuthPrompt.value.copied = true
  if (youtubeOAuthCopyTimer) clearTimeout(youtubeOAuthCopyTimer)
  youtubeOAuthCopyTimer = setTimeout(() => {
    youtubeOAuthPrompt.value.copied = false
  }, 2000)
}

const enrichedPlugins = computed(() => {
  const resultsMap = new Map()
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result)
    })
  }
  const loginResultMap = loginStatusResults.value || {}
  const loginTestingMap = loginStatusTesting.value || {}

  return (plugins.value || []).map((plugin) => {
    const primarySite = plugin.sites?.[0] || null
    const siteName = primarySite?.site_name || primarySite?.name || ''
    const siteResult = resultsMap.get(siteName) || {}
    const loginStatus = loginResultMap[siteName]

    return {
      ...plugin,
      capabilities: Array.isArray(plugin.capabilities) ? plugin.capabilities : [],
      sites: Array.isArray(plugin.sites) ? plugin.sites : [],
      primarySite,
      siteName,
      siteAccessible: siteResult.accessible,
      siteTesting: !!siteResult.testing,
      siteLoginStatus: loginStatus,
      siteOAuthStatus: loginStatus?.oauth_status || null,
      siteOAuthAccount: loginStatus?.oauth_account || null,
      siteLoginTesting: !!loginTestingMap[siteName],
      siteSupportsLogin: primarySite?.supports_login_status ?? false,
      siteDesktopLoginSupported: DESKTOP_LOGIN_SITES.has(String(siteName || '').toLowerCase()),
    }
  })
})

const displayPlugins = computed(() => {
  let list = enrichedPlugins.value

  if (searchQuery.value.trim()) {
    const keyword = searchQuery.value.trim().toLowerCase()
    list = list.filter(p =>
      p.display_name?.toLowerCase().includes(keyword) ||
      p.plugin_id?.toLowerCase().includes(keyword) ||
      p.description?.toLowerCase().includes(keyword) ||
      p.siteName?.toLowerCase().includes(keyword)
    )
  }

  return list
})

const pluginSummary = computed(() => ({
  total: enrichedPlugins.value.length,
  running: enrichedPlugins.value.filter(plugin => plugin.enabled && plugin.active_runtime?.state === 'running').length,
  attention: enrichedPlugins.value.filter((plugin) => {
    if (!plugin.enabled) return true
    if (!plugin.active_runtime) return true
    if (plugin.health?.healthy === false) return true
    return ['failed', 'degraded', 'disabled', 'stopped', 'uninstalled'].includes(plugin.status)
      || ['failed', 'stopped', 'draining'].includes(plugin.active_runtime?.state)
  }).length,
}))

const connectivitySummary = computed(() => {
  if (connectivityResults.value.length === 0) {
    return { total: 0, accessible: 0, failed: 0, success_rate: 0 }
  }
  return connectivityResults.value[0]?.summary || { total: 0, accessible: 0, failed: 0, success_rate: 0 }
})

const handleFileChange = (event) => {
  const [file] = event.target.files || []
  selectedFile.value = file || null
}

const handleInstall = async () => {
  if (!selectedFile.value) return
  installing.value = true
  const res = await installPlugin(selectedFile.value)
  if (!res.error) {
    selectedFile.value = null
    await fetchPlugins()
  }
  installing.value = false
}

const handleCookiesFileChange = (event) => {
  const file = event.target.files?.[0]
  selectedCookiesFile.value = file || null
  cookiesFileName.value = file ? file.name : ''
}

const handleImportAllCookies = async () => {
  if (!selectedCookiesFile.value || importingCookies.value) return
  importingCookies.value = true
  const result = await importAllSiteCookies(selectedCookiesFile.value)
  if (result.error) {
    Logger.error('Failed to import cookies', result.error)
  } else if (shouldRefreshLoginStatusesAfterCookieImport(result.data)) {
    if (supportedSites.value.length === 0) await fetchSupportedSites()
    clearLoginStatusCache()
    await testLoginForAllSupportedSites()
    saveResultsToCache()
  }
  importingCookies.value = false
}

const handleReload = async () => {
  reloading.value = true
  const res = await reloadPlugins()
  if (!res.error) await fetchPlugins()
  reloading.value = false
}

const handleEnable = async (plugin) => {
  actioning.value = plugin.plugin_id
  const res = await enablePlugin(plugin.plugin_id)
  if (!res.error) await fetchPlugins()
  actioning.value = null
}

const handleDisable = async (plugin) => {
  actioning.value = plugin.plugin_id
  const res = await disablePlugin(plugin.plugin_id)
  if (!res.error) await fetchPlugins()
  actioning.value = null
}

const openUninstallDialog = (plugin) => {
  uninstallTarget.value = plugin
  showUninstallDialog.value = true
}

const confirmUninstall = async () => {
  if (!uninstallTarget.value) return
  showUninstallDialog.value = false
  actioning.value = uninstallTarget.value.plugin_id
  const res = await uninstallPlugin(uninstallTarget.value.plugin_id)
  if (!res.error) await fetchPlugins()
  actioning.value = null
  uninstallTarget.value = null
}

const handleTestAll = async () => {
  testingAll.value = true
  try {
    const result = await testAllSitesConnectivity()
    if (!result.error && result.data) {
      connectivityResults.value = [result.data]
    }
    await testLoginForAllSupportedSites()
    saveResultsToCache()
  } finally {
    testingAll.value = false
  }
}

const handleTestSingleBySite = async (siteName) => {
  if (!siteName) return
  const result = await testSiteConnectivity(siteName)
  if (!result.error && result.data) {
    if (connectivityResults.value.length === 0) {
      connectivityResults.value = [{ results: [], summary: { total: 0, accessible: 0, failed: 0, success_rate: 0 } }]
    }
    const results = connectivityResults.value[0].results
    const existingIndex = results.findIndex(r => r.site_name === siteName)
    if (existingIndex !== -1) results[existingIndex] = result.data
    else results.push(result.data)

    const accessible = results.filter(r => r.accessible).length
    connectivityResults.value[0].summary = {
      total: results.length,
      accessible,
      failed: results.length - accessible,
      success_rate: results.length > 0 ? Math.round((accessible / results.length) * 100) : 0
    }
    saveResultsToCache()
  }
}

const handleTestLoginBySite = async (siteName) => {
  if (!siteName) return
  loginStatusTesting.value[siteName] = true
  try {
    const bridge = getDesktopBridge()
    if (
      bridge?.isDesktop === true
      && DESKTOP_LOGIN_SITES.has(String(siteName || '').toLowerCase())
      && typeof bridge.getSiteLoginStatus === 'function'
    ) {
      const result = await bridge.getSiteLoginStatus(siteName)
      if (result) upsertLoginStatus(siteName, result)
      return
    }

    const { data, error } = await testSiteLoginStatus(siteName)
    if (!error && data) upsertLoginStatus(siteName, data)
    else {
      upsertLoginStatus(siteName, {
        site_name: siteName,
        logged_in: false,
        message: error?.message || '检测失败',
        checked_at: new Date().toISOString(),
      })
    }
  } finally {
    loginStatusTesting.value[siteName] = false
    saveResultsToCache()
  }
}

const getDesktopBridge = () => window.desktopApp || null

const handleDesktopSiteLogin = async (siteName) => {
  if (!siteName) return
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop !== true || typeof bridge.openSiteLogin !== 'function') return

  loginStatusTesting.value[siteName] = true
  try {
    showToast('桌面登录窗口已打开，手机确认后会自动完成')
    const result = await bridge.openSiteLogin(siteName)
    if (result) {
      upsertLoginStatus(siteName, result)
      showToast(result.logged_in ? '桌面登录成功' : (result.message || '未检测到桌面登录态'), !result.logged_in)
    }
  } catch (error) {
    Logger.error('Failed to open desktop site login', error)
    upsertLoginStatus(siteName, {
      site_name: siteName,
      supported: true,
      logged_in: false,
      message: '桌面登录窗口打开失败',
      checked_at: new Date().toISOString(),
      source: 'desktop',
    })
    showToast('桌面登录窗口打开失败', true)
  } finally {
    loginStatusTesting.value[siteName] = false
    saveResultsToCache()
  }
}

const handleClearDesktopSiteSession = async (siteName) => {
  if (!siteName) return
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop !== true || typeof bridge.clearSiteSession !== 'function') return

  loginStatusTesting.value[siteName] = true
  try {
    const result = await bridge.clearSiteSession(siteName)
    if (result) {
      upsertLoginStatus(siteName, result)
      showToast('桌面会话已清除')
    }
  } catch (error) {
    Logger.error('Failed to clear desktop site session', error)
    upsertLoginStatus(siteName, {
      site_name: siteName,
      supported: true,
      logged_in: false,
      message: '清除桌面会话失败',
      checked_at: new Date().toISOString(),
      source: 'desktop',
    })
    showToast('清除桌面会话失败', true)
  } finally {
    loginStatusTesting.value[siteName] = false
    saveResultsToCache()
  }
}

const upsertLoginStatus = (siteName, payload) => {
  loginStatusResults.value = {
    ...loginStatusResults.value,
    [siteName]: mergeLoginStatusResult(loginStatusResults.value?.[siteName], payload)
  }
}

const openSiteEditorByPlugin = (plugin) => {
  const siteName = plugin.siteName
  if (!siteName) return
  const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || {}
  editingSite.value = {
    slug: siteName,
    label: catalogInfo.label || plugin.display_name || siteName,
    enabled: catalogInfo.enabled !== false,
    test_url: catalogInfo.test_url || '',
    domains: catalogInfo.domains || [],
    iconUrl: catalogInfo.icon_url || '',
  }
  siteEditorVisible.value = true
}

const closeSiteEditor = () => {
  siteEditorVisible.value = false
  editingSite.value = null
}

const saveSiteEditor = async ({ slug, sitePayload }) => {
  siteEditorSaving.value = true
  try {
    await saveCatalog({ [slug]: sitePayload })
    siteEditorVisible.value = false
  } catch (error) {
    Logger.error('Failed to save site config', error)
  } finally {
    siteEditorSaving.value = false
  }
}

const fetchPlugins = async () => {
  loading.value = true
  const { data, error } = await getPlugins()
  if (!error) plugins.value = data || []
  loading.value = false
}

const fetchSupportedSites = async () => {
  const { data, error } = await getSupportedSites()
  if (!error && data) supportedSites.value = data.sites || []
}

const testLoginForAllSupportedSites = async () => {
  const targets = supportedSites.value.filter(site => site.supports_login_status)
  await Promise.all(targets.map(site => handleTestLoginBySite(site.site_name || site.name)))
}

const getPluginStatusText = (plugin) => {
  if (!plugin.enabled) return '停用'
  if (plugin.active_runtime?.state === 'running') return '运行'
  if (plugin.health?.healthy === false || plugin.active_runtime?.state === 'failed') return '异常'
  return '待检查'
}

const getPluginStatusClass = (plugin) => {
  if (!plugin.enabled) return 'border-border/50 bg-muted text-muted-foreground'
  if (plugin.active_runtime?.state === 'running') return 'border-border/50 bg-background text-foreground'
  if (plugin.health?.healthy === false || plugin.active_runtime?.state === 'failed') return 'border-destructive/20 bg-destructive/10 text-destructive'
  return 'border-border/50 bg-muted text-muted-foreground'
}

const getNetworkText = (plugin) => {
  if (plugin.siteAccessible === true) return '正常'
  if (plugin.siteAccessible === false) return '失败'
  return '未检测'
}

const getLoginText = (plugin) => {
  if (plugin.siteOAuthStatus === 'authenticated') return '有效'
  if (plugin.siteOAuthStatus === 'pending') return '授权中'
  if (plugin.siteLoginStatus?.supported === false) return '不支持'
  if (plugin.siteLoginStatus?.source === 'desktop') return plugin.siteLoginStatus?.logged_in ? '桌面已登录' : '桌面未登录'
  if (plugin.siteLoginStatus?.logged_in) return '有效'
  if (plugin.siteLoginStatus) return '失效'
  return '未检测'
}

const getCapabilityLabel = (name) => CAPABILITY_LABELS[name] || name

const formatTime = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const openExternalUrl = async (targetUrl) => {
  const url = String(targetUrl || '').trim()
  if (!url) return
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop === true && typeof bridge.openExternal === 'function') {
    await bridge.openExternal(url)
    return
  }
  window.open(url, '_blank')
}

const handleStartYouTubeOAuth = async () => {
  youtubeOAuthPrompt.value.dismissedCode = ''
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop === true && typeof bridge.openSiteLogin === 'function') {
    const result = await bridge.openSiteLogin('youtube')
    if (result) {
      upsertLoginStatus('youtube', result)
      await openExternalUrl(result.verification_url)
      showYouTubeOAuthPrompt({
        verificationUrl: result.verification_url,
        userCode: result.user_code,
      })
      if (result.oauth_status === 'pending') startYouTubeOAuthPolling()
    }
    return
  }

  const { data, error } = await setupYouTubeOAuth()
  if (!error && data) {
    if (data.verification_url) await openExternalUrl(data.verification_url)
    showYouTubeOAuthPrompt({
      verificationUrl: data.verification_url || '',
      userCode: data.user_code || '',
    })
    upsertLoginStatus('youtube', {
      site_name: 'youtube',
      supported: true,
      logged_in: data.status === 'authenticated',
      message: data.status === 'pending' ? 'TV 授权中' : (data.status === 'authenticated' ? 'TV 授权有效' : '未配置 TV 授权'),
      checked_at: new Date().toISOString(),
      oauth_status: data.status,
      oauth_account: data.account || null,
      verification_url: data.verification_url || null,
      user_code: data.user_code || null,
    })
    if (data.status === 'pending') startYouTubeOAuthPolling()
  }
}

const handleRevokeYouTubeOAuth = async () => {
  hideYouTubeOAuthPrompt()
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop === true && typeof bridge.clearSiteSession === 'function') {
    const result = await bridge.clearSiteSession('youtube')
    if (result) upsertLoginStatus('youtube', result)
  } else {
    await revokeYouTubeOAuth()
  }
  stopYouTubeOAuthPolling()
  fetchPlugins()
}

const startYouTubeOAuthPolling = () => {
  stopYouTubeOAuthPolling()
  ytOAuthPollTimer = setInterval(async () => {
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop === true && typeof bridge.getSiteLoginStatus === 'function') {
      const result = await bridge.getSiteLoginStatus('youtube')
      if (result) upsertLoginStatus('youtube', result)
      if (result?.oauth_status === 'pending') {
        showYouTubeOAuthPrompt({
          verificationUrl: result.verification_url,
          userCode: result.user_code,
        })
      } else {
        hideYouTubeOAuthPrompt()
        stopYouTubeOAuthPolling()
      }
      return
    }

    const { data } = await getYouTubeOAuthStatus()
    if (data) {
      if (data.status === 'pending') {
        showYouTubeOAuthPrompt({
          verificationUrl: data.verification_url || '',
          userCode: data.user_code || '',
        })
      } else {
        hideYouTubeOAuthPrompt()
      }
      upsertLoginStatus('youtube', {
        site_name: 'youtube',
        supported: true,
        logged_in: data.status === 'authenticated',
        message: data.status === 'pending' ? 'TV 授权中' : (data.status === 'authenticated' ? 'TV 授权有效' : '未配置 TV 授权'),
        checked_at: new Date().toISOString(),
        oauth_status: data.status,
        oauth_account: data.account || null,
        verification_url: data.verification_url || null,
        user_code: data.user_code || null,
      })
    }
    if (data?.status !== 'pending') stopYouTubeOAuthPolling()
  }, 3000)
}

const stopYouTubeOAuthPolling = () => {
  if (ytOAuthPollTimer) clearInterval(ytOAuthPollTimer)
  ytOAuthPollTimer = null
}

const cleanupYouTubeOAuthUi = () => {
  stopYouTubeOAuthPolling()
  if (youtubeOAuthCopyTimer) clearTimeout(youtubeOAuthCopyTimer)
  youtubeOAuthCopyTimer = null
}

onMounted(() => {
  fetchPlugins()
  loadCatalog()
  loadResultsFromCache()
  fetchSupportedSites()
})

onUnmounted(cleanupYouTubeOAuthUi)
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}

.plugin-grid {
  display: grid;
  grid-template-columns: minmax(18rem, 1fr) 7rem 12rem 7rem 7rem 15rem;
  gap: 1rem;
}

.custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>

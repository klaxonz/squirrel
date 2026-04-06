<template>
  <div class="plugin-manager bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-4 pb-4">
      <PageHeader
        title="插件管理"
        description="管理扩展资产与站点连通性，把插件状态、Cookie、登录检测和可访问性放在同一套运营视图里。"
      >
        <template #actions>
          <div class="plugin-tab-switch">
            <button
              @click="currentTab = 'plugins'"
              class="plugin-tab-switch__button"
              :class="{ 'plugin-tab-switch__button--active': currentTab === 'plugins' }"
            >
              插件列表
            </button>
            <button
              @click="currentTab = 'connectivity'"
              class="plugin-tab-switch__button"
              :class="{ 'plugin-tab-switch__button--active': currentTab === 'connectivity' }"
            >
              站点连通性
            </button>
          </div>
          <div class="plugin-hero__actions">
            <template v-if="currentTab === 'plugins'">
              <Button as-child variant="outline" size="sm" class="plugin-upload-button cursor-pointer">
                <label>
                  <input
                    type="file"
                    accept=".zip"
                    class="hidden"
                    @change="handleFileChange"
                  />
                  <CloudArrowUpIcon class="w-4 h-4" />
                  <span class="truncate max-w-[180px]">{{ selectedFile ? selectedFile.name : '选择文件' }}</span>
                </label>
              </Button>
              <Button
                :disabled="!selectedFile || installing"
                @click="handleInstall"
                size="sm"
                class="plugin-primary-action"
              >
                {{ installing ? '安装中...' : '导入插件' }}
              </Button>
              <Button
                :disabled="reloading || loading"
                @click="handleReload"
                size="icon-sm"
                variant="outline"
                class="plugin-pill-icon"
                title="重新加载插件"
              >
                <ArrowPathIcon class="w-4 h-4" :class="{ 'animate-spin': reloading }" />
              </Button>
            </template>
            <template v-else>
              <Button as-child variant="outline" size="sm" class="plugin-upload-button cursor-pointer text-xs md:text-sm">
                <label>
                  <input
                    type="file"
                    accept=".txt"
                    class="hidden"
                    @change="handleCookiesFileChange"
                  />
                  <span class="truncate max-w-[180px]" :title="cookiesFileName || '选择 cookies.txt 文件'">
                    {{ cookiesFileName || '选择 cookies.txt 文件' }}
                  </span>
                </label>
              </Button>
              <Button
                @click="handleImportAllCookies"
                :disabled="!selectedCookiesFile || importingCookies"
                size="sm"
                variant="outline"
                class="text-xs md:text-sm"
              >
                {{ importingCookies ? '导入中...' : '导入所有站点 Cookie' }}
              </Button>
              <Button
                @click="handleSyncCookieCloud"
                :disabled="syncingCookieCloud"
                size="sm"
                variant="outline"
                class="text-xs md:text-sm"
              >
                {{ syncingCookieCloud ? '同步中...' : '从 CookieCloud 同步' }}
              </Button>
              <Button
                @click="handleTestAll"
                :disabled="testingAll || loadingSites"
                size="sm"
                class="plugin-primary-action"
              >
                <ArrowPathIcon v-if="testingAll" class="w-4 h-4 animate-spin" />
                <CheckCircleIcon v-else class="w-4 h-4" />
                {{ testingAll ? '测试中...' : '测试全部' }}
              </Button>
            </template>
          </div>
        </template>
      </PageHeader>
    </div>

    <div class="content-container pb-10 flex-1 min-h-0 space-y-8">
      <div v-if="currentTab === 'plugins'" class="space-y-6">
        <!-- Summary Stats -->
        <div class="flex flex-wrap items-end justify-between gap-6 py-2 border-b border-border/50">
          <div class="flex flex-wrap gap-8">
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">总插件数</span>
              <span class="text-2xl font-semibold tabular-nums">{{ pluginSummary.total }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">运行中</span>
              <span class="text-2xl font-semibold tabular-nums">{{ pluginSummary.running }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">异常或停用</span>
              <span class="text-2xl font-semibold text-warning tabular-nums">{{ pluginSummary.attention }}</span>
            </div>
          </div>
          
          <div class="relative w-full md:w-64">
            <MagnifyingGlassIcon class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
            <Input 
              v-model="searchQuery" 
              placeholder="搜索插件..." 
              class="pl-9 h-8 text-xs bg-muted/20 border-border/40 focus:bg-background transition-all"
            />
          </div>
        </div>

        <div v-if="loading" class="flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-foreground"></div>
        </div>

        <div v-else-if="plugins.length === 0" class="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border rounded-lg">
          <CubeIcon class="w-12 h-12 mb-4 opacity-20" />
          <p class="text-sm">暂无插件</p>
          <p class="text-xs mt-1">请导入插件 ZIP 包</p>
        </div>

        <div v-else class="plugin-rack space-y-3">
          <div v-for="plugin in displayPlugins" :key="plugin.plugin_id" class="rack-unit group transition-all duration-300 hover:bg-white/[0.04]">
            <div class="unit-content flex-1 p-4 flex items-center gap-6">
              <div class="flex flex-col items-center gap-1">
                <div class="led-indicator" :class="getLedClass(plugin)"></div>
                <span class="text-[8px] font-bold opacity-30 tracking-tighter">状态</span>
              </div>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-3 mb-1">
                  <SiteIcon
                    v-if="plugin.primarySite"
                    :icon-url="plugin.primarySite.icon_url"
                    :label="plugin.primarySite.site_name || plugin.display_name"
                    size="sm"
                    class="shadow-sm"
                  />
                  <span class="unit-title text-sm font-bold uppercase tracking-tight text-foreground/90">{{ plugin.display_name }}</span>
                  <div class="unit-id px-1.5 py-0.5 border border-white/10 rounded bg-black/40">
                    {{ plugin.plugin_id }} v{{ plugin.version }}
                  </div>
                </div>
                <div class="text-[10px] text-muted-foreground/60 font-mono truncate max-w-xl">
                  {{ plugin.description || '暂无描述' }} // 端点: {{ plugin.active_runtime?.endpoint || '离线' }}
                </div>
              </div>

              <div class="flex items-center gap-8 px-6 border-x border-white/5 hidden lg:flex">
                <div class="flex flex-col gap-1">
                  <span class="text-[8px] font-bold opacity-30 tracking-widest">能力</span>
                  <div class="flex gap-1">
                    <span v-for="cap in plugin.capabilities.slice(0, 3)" :key="cap.name" class="text-[9px] font-mono text-orange-500/80">[{{ cap.name }}]</span>
                  </div>
                </div>
                <div class="flex flex-col gap-1">
                  <span class="text-[8px] font-bold opacity-30 tracking-widest">目标站点</span>
                  <div class="flex items-center gap-2 text-[9px] font-mono text-white/40">
                    <SiteIcon
                      v-if="plugin.primarySite"
                      :icon-url="plugin.primarySite.icon_url"
                      :label="plugin.primarySite.site_name"
                      size="xs"
                    />
                    <span>{{ formatSiteNames(plugin.sites) }}</span>
                  </div>
                </div>
              </div>

              <div class="flex items-center justify-end gap-2">
                <Button
                  v-if="!plugin.enabled"
                  :disabled="actioning === plugin.plugin_id"
                  @click="handleEnable(plugin)"
                  variant="ghost"
                  size="sm"
                  class="h-7 text-[10px] px-3 font-bold tracking-tight bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20"
                >
                  启用
                </Button>
                <Button
                  v-if="plugin.enabled"
                  :disabled="actioning === plugin.plugin_id"
                  @click="handleDisable(plugin)"
                  variant="ghost"
                  size="sm"
                  class="h-7 text-[10px] px-3 font-bold tracking-tight bg-white/5 text-white/60 hover:bg-white/10"
                >
                  停用
                </Button>
                <Button
                  :disabled="actioning === plugin.plugin_id"
                  @click="handleUninstall(plugin)"
                  variant="ghost"
                  size="sm"
                  class="h-7 text-[10px] px-3 font-bold tracking-tight text-rose-500/60 hover:text-rose-500 hover:bg-rose-500/10"
                >
                  卸载
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="currentTab === 'connectivity'" class="space-y-6">
        <!-- Connectivity Summary -->
        <div class="flex flex-wrap items-end justify-between gap-6 py-2 border-b border-border/50">
          <div v-if="connectivityResults.length > 0" class="flex flex-wrap gap-10">
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">总站点数</span>
              <span class="text-2xl font-semibold tabular-nums">{{ connectivitySummary.total }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">可访问</span>
              <span class="text-2xl font-semibold text-success tabular-nums">{{ connectivitySummary.accessible }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">不可访问</span>
              <span class="text-2xl font-semibold text-destructive tabular-nums">{{ connectivitySummary.failed }}</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1">成功率</span>
              <span class="text-2xl font-semibold tabular-nums">{{ connectivitySummary.success_rate }}%</span>
            </div>
          </div>
          
          <div class="relative w-full md:w-64">
            <MagnifyingGlassIcon class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
            <Input 
              v-model="siteSearchQuery" 
              placeholder="搜索站点或域名..." 
              class="pl-9 h-8 text-xs bg-muted/20 border-border/40 focus:bg-background transition-all"
            />
          </div>
        </div>

        <div v-if="lastTestedAt" class="text-[10px] font-bold tracking-widest text-muted-foreground/40 bg-muted/20 px-3 py-1.5 rounded border border-border/30 inline-block">
          最近检测: {{ formatTime(lastTestedAt) }}
        </div>

        <div v-if="loadingSites" class="flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-foreground"></div>
        </div>

        <div v-else class="overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full border-collapse">
              <thead>
                <tr class="border-b border-border text-left">
                  <th class="py-3 px-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">站点标识</th>
                  <th class="py-3 px-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 hidden lg:table-cell">解析范围</th>
                  <th class="py-3 px-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 text-center">网络通路</th>
                  <th class="py-3 px-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 text-center">凭据验证</th>
                  <th class="py-3 px-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 text-center">响应延迟</th>
                  <th class="py-3 px-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 text-right">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/40">
                <tr
                  v-for="site in displaySites"
                  :key="site.site_name"
                  class="group hover:bg-muted/20 transition-colors"
                >
                  <td class="py-4 px-2">
                    <div class="flex items-start gap-3">
                      <SiteIcon
                        :icon-url="site.icon_url"
                        :label="site.display_label || site.site_name || site.name"
                        size="sm"
                        class="mt-0.5"
                      />
                      <div class="flex flex-col">
                      <div class="flex items-center gap-2 mb-0.5">
                        <span class="text-sm font-semibold tracking-tight text-foreground/90">{{ site.display_label || site.site_name || site.name }}</span>
                        <span
                          v-if="site.config_enabled === false"
                          class="text-[9px] font-bold px-1 py-0 bg-destructive/10 text-destructive rounded-[3px] tracking-tighter"
                        >
                          已禁用
                        </span>
                      </div>
                      <div class="text-[10px] text-muted-foreground/60 flex items-center gap-2 font-mono">
                        <span>{{ site.site_name || site.name }}</span>
                        <span v-if="site.test_url" class="opacity-30">•</span>
                        <span v-if="site.test_url" class="truncate max-w-[150px] opacity-50">{{ site.test_url }}</span>
                      </div>
                    </div>
                    </div>
                  </td>
                  <td class="py-4 px-2 hidden lg:table-cell">
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="domain in site.domains?.slice(0, 2) || []"
                        :key="domain"
                        class="text-[9px] font-bold px-1.5 py-0 bg-muted/60 text-muted-foreground/60 rounded-[3px]"
                      >
                        {{ domain }}
                      </span>
                      <span
                        v-if="site.domains?.length > 2"
                        class="text-[9px] text-muted-foreground/30 font-bold"
                      >
                        +{{ site.domains.length - 2 }}
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-2">
                    <div class="flex justify-center">
                      <div v-if="site.testing" class="flex items-center gap-2 text-muted-foreground/40 animate-pulse">
                        <ArrowPathIcon class="w-3 h-3 animate-spin" />
                        <span class="text-[10px] font-bold">检测中...</span>
                      </div>
                      <div
                        v-else-if="site.accessible === true || site.accessible === false"
                        class="flex items-center gap-2"
                        :class="getSiteConnectivityClass(site)"
                        :title="getSiteConnectivityBadge(site).title"
                      >
                        <div class="w-1.5 h-1.5 rounded-full" :class="getSiteConnectivityIndicatorClass(site)"></div>
                        <span class="text-[10px] font-bold uppercase tracking-wider">{{ getSiteConnectivityBadge(site).label }}</span>
                      </div>
                      <span v-else class="text-[10px] font-bold text-muted-foreground/30">未检测</span>
                    </div>
                  </td>
                  <td class="py-4 px-2">
                    <div class="flex justify-center">
                      <div v-if="!site.supports_login_status" class="text-[10px] font-bold text-muted-foreground/20 tracking-widest">
                        不适用
                      </div>
                      <div v-else-if="site.loginTesting" class="flex items-center gap-2 text-muted-foreground/40 animate-pulse">
                        <ArrowPathIcon class="w-3 h-3 animate-spin" />
                        <span class="text-[10px] font-bold">验证中...</span>
                      </div>
                      <div
                        v-else-if="site.loginStatus?.logged_in"
                        class="flex items-center gap-2 text-success/80"
                        :title="site.loginStatus?.message || '已登录'"
                      >
                        <CheckCircleIcon class="w-3.5 h-3.5" />
                        <span class="text-[10px] font-bold tracking-wider">有效</span>
                      </div>
                      <div
                        v-else-if="site.loginStatus"
                        class="flex items-center gap-2"
                        :class="getSiteLoginStatusClass(site)"
                        :title="getSiteLoginBadge(site).title"
                      >
                        <div class="w-1.5 h-1.5 rounded-full" :class="getSiteLoginStatusIndicatorClass(site)"></div>
                        <span class="text-[10px] font-bold uppercase tracking-wider">{{ getSiteLoginBadge(site).label }}</span>
                      </div>
                      <span v-else class="text-[10px] font-bold text-muted-foreground/30 tracking-wider">未测试</span>
                    </div>
                  </td>
                  <td class="py-4 px-2 text-center">
                    <span v-if="site.response_time" class="text-[10px] font-bold font-mono text-muted-foreground/70 tabular-nums" :class="site.response_time > 1000 ? 'text-warning/80' : ''">
                      {{ site.response_time }}ms
                    </span>
                    <span v-else class="text-muted-foreground/20 font-mono">—</span>
                  </td>
                  <td class="py-4 px-2">
                    <div class="flex items-center justify-end gap-1">
                      <Button
                        @click="handleTestSingle(site)"
                        :disabled="site.testing || testingAll"
                        variant="ghost"
                        size="sm"
                        class="h-7 text-[10px] px-2 font-bold tracking-tight"
                      >
                        测试
                      </Button>
                      <Button
                        v-if="site.supports_login_status"
                        @click="handleTestLogin(site)"
                        :disabled="site.loginTesting || testingAll"
                        variant="ghost"
                        size="sm"
                        class="h-7 text-[10px] px-2 font-bold tracking-tight"
                      >
                        验证
                      </Button>
                      <Button
                        @click="handleUploadCookies(site)"
                        :disabled="site.cookieUploading || testingAll"
                        variant="ghost"
                        size="sm"
                        class="h-7 text-[10px] px-2 font-bold tracking-tight"
                      >
                        Cookie
                      </Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <SiteConfigEditorDialog
      :visible="siteEditorVisible"
      :site="editingSite"
      :catalog="siteCatalog"
      :saving="siteEditorSaving"
      :error-message="siteEditorError"
      @close="closeSiteEditor"
      @save="saveSiteEditor"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch } from 'vue';
import {
  CloudArrowUpIcon,
  ArrowPathIcon,
  CubeIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/vue/24/outline';
import PageHeader from '@/components/layout/PageHeader.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getConnectivityBadge } from '@/utils/plugin-connectivity-status'
import { Logger } from '@/utils/logger'
import { getLoginStatusBadge, mergeLoginStatusResult, shouldRefreshLoginStatusesAfterCookieImport } from '@/utils/plugin-login-status'
import { useSiteCatalog } from '@/composables/useSites';
import {
  disablePlugin,
  enablePlugin,
  getPlugins,
  getSupportedSites,
  importAllSiteCookies,
  installPlugin,
  reloadPlugins,
  syncCookieCloudCookies,
  testAllSitesConnectivity,
  testSiteConnectivity,
  testSiteLoginStatus,
  uninstallPlugin,
  uploadSiteCookies,
} from '@/api'

// 插件管理相关状态
const currentTab = ref('plugins');
const loading = ref(false);
const installing = ref(false);
const reloading = ref(false);
const plugins = ref([]);
const selectedFile = ref(null);
const actioning = ref(null);

// 站点连通性测试相关状态
const loadingSites = ref(false);
const testingAll = ref(false);
const supportedSites = ref([]);
const connectivityResults = ref([]);
const loginStatusResults = ref({});
const loginStatusTesting = ref({});
const cookieUploading = ref({});
const lastTestedAt = ref(null);

// 缓存相关常量
const CACHE_KEY_CONNECTIVITY = 'squirrel_connectivity_results';
const CACHE_KEY_LOGIN_STATUS = 'squirrel_login_status_results';
const CACHE_KEY_LAST_TESTED = 'squirrel_last_tested_at';

const clearLoginStatusCache = () => {
  loginStatusResults.value = {};
  try {
    localStorage.removeItem(CACHE_KEY_LOGIN_STATUS);
  } catch (e) {
    Logger.warn('Failed to clear login status cache', e);
  }
};

// 缓存函数
const saveResultsToCache = () => {
  try {
    if (connectivityResults.value.length > 0) {
      localStorage.setItem(CACHE_KEY_CONNECTIVITY, JSON.stringify(connectivityResults.value));
    }
    if (Object.keys(loginStatusResults.value).length > 0) {
      localStorage.setItem(CACHE_KEY_LOGIN_STATUS, JSON.stringify(loginStatusResults.value));
    }
    const now = new Date().toISOString();
    lastTestedAt.value = now;
    localStorage.setItem(CACHE_KEY_LAST_TESTED, now);
  } catch (e) {
    Logger.warn('Failed to save connectivity cache', e);
  }
};

const loadResultsFromCache = () => {
  try {
    const cachedConnectivity = localStorage.getItem(CACHE_KEY_CONNECTIVITY);
    const cachedLoginStatus = localStorage.getItem(CACHE_KEY_LOGIN_STATUS);
    const cachedLastTested = localStorage.getItem(CACHE_KEY_LAST_TESTED);
    
    if (cachedConnectivity) {
      connectivityResults.value = JSON.parse(cachedConnectivity);
    }
    if (cachedLoginStatus) {
      loginStatusResults.value = JSON.parse(cachedLoginStatus);
    }
    if (cachedLastTested) {
      lastTestedAt.value = cachedLastTested;
    }
  } catch (e) {
    Logger.warn('Failed to load connectivity cache', e);
  }
};

const getSiteConnectivityBadge = (site) => getConnectivityBadge(site);

const getSiteConnectivityClass = (site) => {
  const tone = getSiteConnectivityBadge(site).tone;
  if (tone === 'success') return 'text-success/80';
  if (tone === 'warning') return 'text-warning/80';
  if (tone === 'danger') return 'text-destructive/80';
  return 'text-muted-foreground/40';
};

const getSiteConnectivityIndicatorClass = (site) => {
  const tone = getSiteConnectivityBadge(site).tone;
  if (tone === 'success') return 'bg-success';
  if (tone === 'warning') return 'bg-warning';
  if (tone === 'danger') return 'bg-destructive';
  return 'bg-muted-foreground/30';
};

const getSiteLoginBadge = (site) => getLoginStatusBadge(site?.loginStatus);

const getSiteLoginStatusClass = (site) => {
  const tone = getSiteLoginBadge(site).tone;
  if (tone === 'success') return 'text-success/80';
  if (tone === 'warning') return 'text-warning/80';
  if (tone === 'danger') return 'text-destructive/80';
  return 'text-muted-foreground/40';
};

const getSiteLoginStatusIndicatorClass = (site) => {
  const tone = getSiteLoginBadge(site).tone;
  if (tone === 'success') return 'bg-success';
  if (tone === 'warning') return 'bg-warning';
  if (tone === 'danger') return 'bg-destructive';
  return 'bg-muted-foreground/30';
};

// Cookies 导入（全局 / 单站点复用）
const selectedCookiesFile = ref(null);
const cookiesFileName = ref('');
const importingCookies = ref(false);
const syncingCookieCloud = ref(false);

// 站点配置（数据爬取）
const { catalog: siteCatalog, loading: siteCatalogLoading, error: siteCatalogErrorState, loadCatalog, saveCatalog } = useSiteCatalog();
const siteCatalogLoaded = ref(false);
const editingSite = ref(null);
const siteEditorVisible = ref(false);
const siteEditorSaving = ref(false);
const siteEditorError = ref('');

const siteCatalogMap = computed(() => siteCatalog.value || {});

const pluginStatusLabels = {
  uploaded: '已上传',
  validated: '已校验',
  installed: '已安装',
  starting: '启动中',
  running: '运行中',
  degraded: '降级',
  disabled: '已禁用',
  failed: '异常',
  stopped: '已停止',
  uninstalled: '已卸载',
};

const runtimeStateLabels = {
  starting: '运行时启动中',
  running: '运行时正常',
  draining: '运行时回收中',
  stopped: '运行时已停止',
  failed: '运行时异常',
};

const searchQuery = ref('');
const siteSearchQuery = ref('');

const displayPlugins = computed(() => {
  let list = (plugins.value || []).map((plugin) => {
    const capabilities = Array.isArray(plugin.capabilities) ? plugin.capabilities : [];
    const sites = Array.isArray(plugin.sites) ? plugin.sites : [];
    const permissions = Array.isArray(plugin.permissions) ? plugin.permissions : [];
    const activeRuntime = plugin.active_runtime || null;
    const health = plugin.health || activeRuntime?.health || null;

    return {
      ...plugin,
      capabilities,
      sites,
      primarySite: sites[0] || null,
      permissions,
      active_runtime: activeRuntime,
      health,
      capabilityCount: capabilities.length,
      siteCount: sites.length,
      permissionCount: permissions.length,
      runtimeStateLabel: runtimeStateLabels[activeRuntime?.state] || '运行时未启动',
    };
  });

  if (searchQuery.value.trim()) {
    const keyword = searchQuery.value.trim().toLowerCase();
    list = list.filter(p => 
      p.display_name?.toLowerCase().includes(keyword) || 
      p.plugin_id?.toLowerCase().includes(keyword) ||
      p.description?.toLowerCase().includes(keyword)
    );
  }
  
  return list;
});

const pluginSummary = computed(() => ({
  total: displayPlugins.value.length,
  running: displayPlugins.value.filter(plugin => plugin.enabled && plugin.active_runtime?.state === 'running').length,
  attention: displayPlugins.value.filter((plugin) => {
    if (!plugin.enabled) return true;
    if (!plugin.active_runtime) return true;
    if (plugin.health?.healthy === false) return true;
    return ['failed', 'degraded', 'disabled', 'stopped', 'uninstalled'].includes(plugin.status)
      || ['failed', 'stopped', 'draining'].includes(plugin.active_runtime?.state);
  }).length,
}));

const connectivitySummary = computed(() => {
  if (connectivityResults.value.length === 0) {
    return { total: 0, accessible: 0, failed: 0, success_rate: 0 };
  }
  return connectivityResults.value[0]?.summary || { total: 0, accessible: 0, failed: 0, success_rate: 0 };
});

const getPluginStatusIndicator = (plugin) => {
  if (['running'].includes(plugin.status)) return 'bg-success';
  if (['starting', 'installed', 'validated', 'uploaded'].includes(plugin.status)) return 'bg-info';
  if (['degraded'].includes(plugin.status)) return 'bg-warning';
  if (['failed'].includes(plugin.status)) return 'bg-destructive';
  return 'bg-muted-foreground/30';
};

const getPluginStatusLabel = (plugin) => pluginStatusLabels[plugin.status] || plugin.status || '未知状态';

const getLedClass = (plugin) => {
  if (!plugin.enabled) return 'led-off';
  if (plugin.active_runtime?.state === 'running' && plugin.health?.healthy !== false) return 'led-running';
  if (plugin.active_runtime?.state === 'failed' || plugin.health?.healthy === false) return 'led-failed';
  return 'led-starting';
};

const getPluginHealthLabel = (plugin) => {
  if (!plugin.enabled) return '未启用';
  if (plugin.health?.healthy === true) {
    if (plugin.health?.status === 'ready') return '健康';
    if (plugin.health?.status === 'running') return '运行中';
    return plugin.health?.status || '健康';
  }
  if (plugin.health?.healthy === false) {
    if (plugin.health?.status === 'failed') return '异常';
    return plugin.health?.status || '不健康';
  }
  return plugin.runtimeStateLabel;
};

const getPluginHealthClass = (plugin) => {
  if (!plugin.enabled) return 'plugin-tag--muted';
  if (plugin.health?.healthy === true) return 'plugin-tag--success';
  if (plugin.health?.healthy === false) return 'plugin-tag--danger';
  if (plugin.active_runtime?.state === 'starting') return 'plugin-tag--info';
  return 'plugin-tag--muted';
};

const formatSiteNames = (sites) => {
  const names = (sites || []).map(site => site.site_name || site.label).filter(Boolean);
  if (!names.length) return '未声明站点';
  if (names.length <= 2) return names.join(' / ');
  return `${names.slice(0, 2).join(' / ')} +${names.length - 2}`;
};

const displaySites = computed(() => {
  // 合并支持的站点列表和测试结果
  const resultsMap = new Map();
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result);
    });
  }

  const loginResultMap = loginStatusResults.value || {};
  const loginTestingMap = loginStatusTesting.value || {};

  let list = supportedSites.value.map(siteInfo => {
    const siteName = siteInfo.site_name || siteInfo.name;
    const result = resultsMap.get(siteName);
    const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || null;
    const catalogDomains = catalogInfo?.domains || [];
    const displayLabel = catalogInfo?.label || siteInfo.name;
    
    // 合并站点信息和测试结果
    return {
      ...siteInfo,
      ...result,
      site_name: siteName,
      // 优先使用站点配置中的域名，其次为测试结果、站点定义
      domains: catalogDomains.length > 0 ? catalogDomains : (result?.domains || siteInfo.domains || []),
      test_url: result?.test_url || siteInfo.test_url || '',
      icon_url: siteInfo.icon_url || catalogInfo?.icon_url || '',
      loginStatus: loginResultMap[siteName],
      loginTesting: !!loginTestingMap[siteName],
      supports_login_status: siteInfo.supports_login_status ?? false,
      cookieUploading: !!cookieUploading.value[siteName],
      display_label: displayLabel,
      config_enabled: catalogInfo?.enabled !== false,
      config_aliases: catalogInfo?.aliases || [],
    };
  });

  if (siteSearchQuery.value.trim()) {
    const keyword = siteSearchQuery.value.trim().toLowerCase();
    list = list.filter(s => 
      s.site_name?.toLowerCase().includes(keyword) || 
      s.display_label?.toLowerCase().includes(keyword) ||
      (s.domains && s.domains.some(d => d.toLowerCase().includes(keyword)))
    );
  }

  return list;
});

const handleCookiesFileChange = (event) => {
  const file = event.target.files?.[0];
  selectedCookiesFile.value = file || null;
  cookiesFileName.value = file ? file.name : '';
};

const handleImportAllCookies = async () => {
  if (!selectedCookiesFile.value || importingCookies.value) return;
  importingCookies.value = true;
  const result = await importAllSiteCookies(selectedCookiesFile.value);
  if (result.error) {
    Logger.error('Failed to import cookies for all sites', result.error);
  } else if (shouldRefreshLoginStatusesAfterCookieImport(result.data)) {
    if (supportedSites.value.length === 0) {
      await fetchSupportedSites();
    }
    clearLoginStatusCache();
    await testLoginForAllSupportedSites();
    saveResultsToCache();
  }
  importingCookies.value = false;
};

const handleSyncCookieCloud = async () => {
  if (syncingCookieCloud.value) return;
  syncingCookieCloud.value = true;
  const { data, error } = await syncCookieCloudCookies();
  if (error) {
    alert(error.message || 'CookieCloud 同步失败');
    syncingCookieCloud.value = false;
    return;
  }

  const updatedSites = data?.updated_sites ?? 0;
  if (updatedSites > 0) {
    if (supportedSites.value.length === 0) {
      await fetchSupportedSites();
    }
    clearLoginStatusCache();
    await testLoginForAllSupportedSites();
    saveResultsToCache();
  }
  alert(`CookieCloud 同步完成，更新 ${updatedSites} 个站点`);
  syncingCookieCloud.value = false;
};

const setLoginTesting = (siteName, value) => {
  if (!siteName) return;
  loginStatusTesting.value = {
    ...loginStatusTesting.value,
    [siteName]: value
  };
};

const upsertLoginStatus = (siteName, payload) => {
  if (!siteName) return;
  loginStatusResults.value = {
    ...loginStatusResults.value,
    [siteName]: mergeLoginStatusResult(loginStatusResults.value?.[siteName], payload)
  };
};

const loadSiteCatalog = async () => {
  try {
    await loadCatalog();
    siteCatalogLoaded.value = !siteCatalogErrorState.value;
  } catch (error) {
    Logger.error('Failed to load site config', error);
    siteCatalogLoaded.value = false;
  }
};

const openSiteEditor = async (site) => {
  if (!siteCatalogLoaded.value && !siteCatalogLoading.value) {
    await loadSiteCatalog();
  }
  editingSite.value = site;
  siteEditorError.value = '';
  siteEditorVisible.value = true;
};

const closeSiteEditor = () => {
  siteEditorVisible.value = false;
  editingSite.value = null;
  siteEditorError.value = '';
};

const saveSiteEditor = async ({ slug, sitePayload }) => {
  siteEditorError.value = '';
  const updatedCatalog = { ...siteCatalog.value };
  updatedCatalog[slug] = sitePayload;

  siteEditorSaving.value = true;
  try {
    await saveCatalog(updatedCatalog);
    siteEditorVisible.value = false;
  } catch (error) {
    Logger.error('Failed to save site config', error);
    siteEditorError.value = error?.message || '保存站点配置失败';
  } finally {
    siteEditorSaving.value = false;
  }
};

const fetchPlugins = async () => {
  loading.value = true;
  const { data, error } = await getPlugins();
  if (!error) {
    plugins.value = data || [];
  }
  loading.value = false;
};

const handleFileChange = (event) => {
  const [file] = event.target.files || [];
  selectedFile.value = file || null;
};

const handleInstall = async () => {
  if (!selectedFile.value) return;
  installing.value = true;
  const res = await installPlugin(selectedFile.value);
  if (!res.error) {
    selectedFile.value = null;
    await fetchPlugins();
  }
  installing.value = false;
};

const handleReload = async () => {
  reloading.value = true;
  const res = await reloadPlugins();
  if (!res.error) {
    await fetchPlugins();
  }
  reloading.value = false;
};

const handleEnable = async (plugin) => {
  actioning.value = plugin.plugin_id;
  const res = await enablePlugin(plugin.plugin_id);
  if (!res.error) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const handleDisable = async (plugin) => {
  actioning.value = plugin.plugin_id;
  const res = await disablePlugin(plugin.plugin_id);
  if (!res.error) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const handleUninstall = async (plugin) => {
  actioning.value = plugin.plugin_id;
  const res = await uninstallPlugin(plugin.plugin_id);
  if (!res.error) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const formatTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch (error) {
    return value;
  }
};

// 获取支持的站点列表
const fetchSupportedSites = async () => {
  loadingSites.value = true;
  const { data, error } = await getSupportedSites();
  if (!error && data) {
    // 新的API返回结构：{ sites: [{name, domains, primary_domain}], total }
    supportedSites.value = data.sites || [];
  }
  loadingSites.value = false;
};

// 测试单个站点
const handleTestSingle = async (site) => {
  const siteName = site.site_name || site.name;
  
  // 设置测试状态
  const index = displaySites.value.findIndex(s => (s.site_name || s.name) === siteName);
  if (index !== -1) {
    displaySites.value[index].testing = true;
  }

  const result = await testSiteConnectivity(siteName);
  
  if (!result.error && result.data) {
    // 更新单个站点的测试结果
    if (connectivityResults.value.length === 0) {
      connectivityResults.value = [{ results: [], summary: { total: 0, accessible: 0, failed: 0, success_rate: 0 } }];
    }
    
    const results = connectivityResults.value[0].results;
    const existingIndex = results.findIndex(r => r.site_name === siteName);
    
    if (existingIndex !== -1) {
      results[existingIndex] = result.data;
    } else {
      results.push(result.data);
    }

    // 重新计算统计信息
    const accessible = results.filter(r => r.accessible).length;
    const failed = results.filter(r => !r.accessible).length;
    connectivityResults.value[0].summary = {
      total: results.length,
      accessible,
      failed,
      success_rate: results.length > 0 ? Math.round((accessible / results.length) * 100 * 100) / 100 : 0
    };
    saveResultsToCache();
  }

  // 清除测试状态
  if (index !== -1) {
    displaySites.value[index].testing = false;
  }
};

const handleTestLogin = async (site) => {
  const siteName = site.site_name || site.name;
  setLoginTesting(siteName, true);

  const { data, error } = await testSiteLoginStatus(siteName);

  if (!error && data) {
    upsertLoginStatus(siteName, data);
  } else {
    upsertLoginStatus(siteName, {
      site_name: siteName,
      logged_in: false,
      message: error?.message || '检测失败',
      supported: false,
      checked_at: new Date().toISOString(),
    });
  }

  setLoginTesting(siteName, false);
  saveResultsToCache();
};

const setCookieUploading = (siteName, value) => {
  cookieUploading.value = {
    ...cookieUploading.value,
    [siteName]: value
  };
};

const handleUploadCookies = (site) => {
  const siteName = site.site_name || site.name;
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.txt,.json';

  input.onchange = async (event) => {
    const files = event.target.files || [];
    if (!files.length) {
      return;
    }

    const file = files[0];
    setCookieUploading(siteName, true);
    try {
      const result = await uploadSiteCookies(siteName, file);
      if (!result.error && result.data?.login_status) {
        upsertLoginStatus(siteName, result.data.login_status);
        saveResultsToCache();
      }
    } finally {
      setCookieUploading(siteName, false);
    }
    input.value = '';
  };

  input.click();
};

const testLoginForAllSupportedSites = async () => {
  const targets = supportedSites.value.filter(site => site.supports_login_status);
  if (!targets.length) return;

  await Promise.all(
    targets.map(async (site) => {
      const siteName = site.site_name || site.name;
      if (!siteName) return;

      setLoginTesting(siteName, true);
      try {
        const result = await testSiteLoginStatus(siteName);
        if (!result.error && result.data) {
          upsertLoginStatus(siteName, result.data);
        } else {
          upsertLoginStatus(siteName, {
            site_name: siteName,
            logged_in: false,
            message: result.error?.message || '检测失败',
            supported: false,
            checked_at: new Date().toISOString(),
          });
        }
      } finally {
        setLoginTesting(siteName, false);
      }
    })
  );
};

// 测试全部站点
const handleTestAll = async () => {
  testingAll.value = true;
  try {
    const result = await testAllSitesConnectivity();
    if (!result.error && result.data) {
      connectivityResults.value = [result.data];
    }
    await testLoginForAllSupportedSites();
    saveResultsToCache();
  } finally {
    testingAll.value = false;
  }
};

// 监听标签页切换
watch(currentTab, async (newTab) => {
  if (newTab === 'connectivity') {
    // 加载缓存的结果
    if (connectivityResults.value.length === 0) {
      loadResultsFromCache();
    }
    // 获取站点列表
    if (supportedSites.value.length === 0) {
      await fetchSupportedSites();
    }
    // 自动触发测试刷新数据
    if (!testingAll.value && supportedSites.value.length > 0) {
      handleTestAll();
    }
  }
});

onMounted(() => {
  fetchPlugins();
  loadSiteCatalog();
});
</script>

<style scoped>
.toolbar-container,
.content-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding-left: 1.5rem;
  padding-right: 1.5rem;
  width: 100%;
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

.plugin-tab-switch {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 6px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--muted) / 0.5);
}

.plugin-tab-switch__button {
  padding: 4px 12px;
  border-radius: 4px;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  font-weight: 500;
  transition: all 150ms ease;
}

.plugin-tab-switch__button:hover {
  color: hsl(var(--foreground));
}

.plugin-tab-switch__button--active {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.rack-unit {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  height: 84px;
  position: relative;
  overflow: hidden;
}

.led-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.led-running { 
  background-color: #10b981; 
  box-shadow: 0 0 10px #10b981; 
  animation: pulse 2s infinite; 
}

.led-failed { 
  background-color: #ef4444; 
  box-shadow: 0 0 10px #ef4444; 
  animation: flash 0.5s infinite; 
}

.led-starting { 
  background-color: #f59e0b; 
  box-shadow: 0 0 10px #f59e0b; 
  opacity: 0.6;
}

.led-off {
  background-color: #374151;
  box-shadow: none;
}

.unit-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.05em;
  opacity: 0.6;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.7; }
}

.plugin-hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

/* Status colors using standard variables */
.text-success { color: hsl(var(--success)); }
.bg-success { background-color: hsl(var(--success)); }
.text-warning { color: hsl(var(--warning)); }
.bg-warning { background-color: hsl(var(--warning)); }
.text-info { color: hsl(var(--info)); }
.bg-info { background-color: hsl(var(--info)); }
.text-destructive { color: hsl(var(--destructive)); }
.bg-destructive { background-color: hsl(var(--destructive)); }

</style>

<template>
  <AppPageShell class="plugin-page" variant="compact" scrollable>
    <AppToolbarFrame bordered>
      <PageHeader title="插件管理" description="扩展系统能力，管理站点数据采集与身份验证">
        <template #actions>
          <div class="flex flex-wrap items-center justify-end gap-3">
            <Button as-child variant="outline" class="h-9 px-4 text-sm font-medium cursor-pointer">
              <label class="cursor-pointer flex items-center">
                <input type="file" accept=".zip" class="hidden" @change="handleFileChange" />
                <AppIcon name="upload" class="h-4 w-4 mr-2" />
                <span>{{ selectedFile ? selectedFile.name : '导入插件' }}</span>
              </label>
            </Button>
            <Button
              v-if="selectedFile"
              :disabled="installing"
              @click="handleInstall"
              class="h-9 px-4 text-sm font-medium"
            >
              <AppIcon v-if="installing" name="refresh" class="h-4 w-4 mr-2 animate-spin" />
              <AppIcon v-else name="plusCircle" class="h-4 w-4 mr-2" />
              安装
            </Button>

            <!-- Import Cookies -->
            <Button as-child variant="outline" class="h-9 px-4 text-sm font-medium cursor-pointer">
              <label class="cursor-pointer flex items-center">
                <input type="file" accept=".txt,.json" class="hidden" @change="handleCookiesFileChange" />
                <AppIcon name="cookie" class="h-4 w-4 mr-2" />
                <span>{{ cookiesFileName || '导入登录凭据' }}</span>
              </label>
            </Button>
            <Button
              v-if="selectedCookiesFile"
              @click="handleImportAllCookies"
              :disabled="importingCookies"
              class="h-9 px-4 text-sm font-medium"
            >
              <AppIcon v-if="importingCookies" name="refresh" class="h-4 w-4 mr-2 animate-spin" />
              <AppIcon v-else name="statusSuccess" class="h-4 w-4 mr-2" />
              导入
            </Button>

            <div class="h-6 w-px bg-border mx-1"></div>

            <Button
              @click="handleTestAll"
              :disabled="testingAll"
              variant="outline"
              class="h-9 px-4 text-sm font-medium"
            >
              <AppIcon v-if="testingAll" name="refresh" class="h-4 w-4 mr-2 animate-spin" />
              <AppIcon v-else name="sync" class="h-4 w-4 mr-2" />
              测试全部
            </Button>
          </div>
        </template>
      </PageHeader>

      <div class="app-stat-strip">
          <div class="app-stat-item">
            <span class="app-status-dot app-status-dot--muted"></span>
            <span>已安装</span>
            <span class="app-stat-value">{{ pluginSummary.total }}</span>
          </div>
          <div class="app-stat-item">
            <span class="app-status-dot bg-emerald-500"></span>
            <span>运行中</span>
            <span class="app-stat-value">{{ pluginSummary.running }}</span>
          </div>
          <div v-if="pluginSummary.attention > 0" class="app-stat-item">
            <span class="app-status-dot bg-rose-500"></span>
            <span>需关注</span>
            <span class="app-stat-value">{{ pluginSummary.attention }}</span>
          </div>
          <div v-if="connectivitySummary.total > 0" class="app-stat-item">
            <span class="app-status-dot bg-blue-500"></span>
            <span>网络连通</span>
            <span class="app-stat-value">{{ connectivitySummary.accessible }}/{{ connectivitySummary.total }}</span>
          </div>
          <span v-if="lastTestedAt" class="text-xs text-muted-foreground ml-auto">最近检测：{{ formatTime(lastTestedAt) }}</span>
        </div>
    </AppToolbarFrame>

    <div class="app-page-content">
      <div class="app-page-toolbar">
        <div class="relative w-72 shrink-0">
          <AppIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            v-model="searchQuery"
            placeholder="搜索插件名称、站点或描述..."
            class="h-9 pl-9 pr-8 text-sm shadow-none w-full"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-muted-foreground"
          >
            <AppIcon name="close" class="h-4 w-4" />
          </button>
        </div>
        
        <Button
          :disabled="reloading || loading"
          variant="ghost"
          @click="handleReload"
          class="h-9 px-3"
        >
          <AppIcon name="refresh" :class="['h-4 w-4 mr-2', reloading ? 'animate-spin' : '']" />
          重载插件库
        </Button>
      </div>

      <div class="app-surface w-full overflow-x-auto flex flex-col">
        <div class="plugin-grid app-table-head gap-4 px-6 py-4 w-full">
          <div>插件详情</div>
          <div class="text-center">状态</div>
          <div>核心能力</div>
          <div class="text-center">网络</div>
          <div class="text-center">登录</div>
          <div class="text-right">操作</div>
        </div>

        <!-- List Content -->
        <div class="divide-y divide-border/60 w-full">
          <div v-if="isInitialLoading" class="w-full p-12 flex flex-col gap-4">
            <div v-for="i in 5" :key="i" class="h-16 w-full bg-muted/40 animate-pulse rounded-lg"></div>
          </div>

          <AppEmptyState
            v-else-if="!displayPlugins.length"
            :title="searchQuery ? '没有匹配的插件' : '暂无插件'"
            :copy="searchQuery ? '尝试更换搜索关键词' : '导入插件压缩包以开始使用'"
            class="w-full py-20"
          />

          <div
            v-for="plugin in displayPlugins"
            :key="plugin.plugin_id"
            class="plugin-grid app-table-row gap-4 px-6 py-5 items-center group w-full"
          >
            <!-- Plugin Info -->
            <div class="flex items-center gap-4 min-w-0">
              <div class="shrink-0">
                <SiteIcon
                  v-if="plugin.primarySite"
                  :icon-url="plugin.primarySite.icon_url"
                  :label="plugin.primarySite.site_name || plugin.display_name"
                  size="md"
                  class="rounded-lg border border-border/60 shadow-sm"
                />
                <div v-else class="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground/60 border border-border">
                  <AppIcon name="cube" class="h-5 w-5" />
                </div>
              </div>
              <div class="min-w-0">
                <h3 class="font-semibold text-foreground text-sm truncate">{{ plugin.display_name }}</h3>
                <p class="text-xs text-muted-foreground line-clamp-1 mt-0.5">{{ plugin.description || '暂无描述' }}</p>
              </div>
            </div>

            <!-- Status -->
            <div class="flex justify-center">
              <div :class="[
                'px-2.5 py-1 rounded-md text-[10px] font-bold border uppercase tracking-wider',
                !plugin.enabled ? 'bg-muted border-border text-muted-foreground' :
                plugin.active_runtime?.state === 'running' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' :
                (plugin.health?.healthy === false || plugin.active_runtime?.state === 'failed') ? 'bg-rose-50 border-rose-100 text-rose-700' :
                'bg-blue-50 border-blue-100 text-blue-700'
              ]">
                {{ !plugin.enabled ? '停用' : plugin.active_runtime?.state === 'running' ? '运行' : '异常' }}
              </div>
            </div>

            <!-- Capabilities -->
            <div class="flex flex-wrap gap-1">
              <span
                v-for="cap in plugin.capabilities.slice(0, 3)"
                :key="cap.name"
                class="px-1.5 py-0.5 rounded bg-muted text-[10px] font-medium text-muted-foreground"
              >
                {{ cap.name }}
              </span>
              <span v-if="plugin.capabilities.length > 3" class="text-[10px] text-muted-foreground font-medium ml-1">
                +{{ plugin.capabilities.length - 3 }}
              </span>
            </div>

            <!-- Network -->
            <div class="flex justify-center">
              <div v-if="plugin.siteTesting" class="animate-spin text-muted-foreground/60">
                <AppIcon name="refresh" class="h-4 w-4" />
              </div>
              <div v-else-if="plugin.siteAccessible === true" class="text-emerald-500" title="网络连通正常">
                <AppIcon name="statusSuccess" class="h-5 w-5" />
              </div>
              <div v-else-if="plugin.siteAccessible === false" class="text-rose-500" title="网络连接失败">
                <AppIcon name="xCircle" class="h-5 w-5" />
              </div>
              <span v-else class="text-muted-foreground/35">—</span>
            </div>

            <!-- Login -->
            <div class="flex justify-center">
              <div v-if="plugin.siteLoginTesting" class="animate-spin text-muted-foreground/60">
                <AppIcon name="refresh" class="h-4 w-4" />
              </div>
              <div v-else-if="plugin.siteOAuthStatus === 'authenticated' || plugin.siteLoginStatus?.logged_in" class="text-emerald-500" title="身份验证有效">
                <AppIcon name="security" class="h-5 w-5" />
              </div>
              <div v-else-if="plugin.siteOAuthStatus === 'pending'" class="text-amber-500 animate-pulse" title="等待授权">
                <AppIcon name="refresh" class="h-5 w-5" />
              </div>
              <div v-else-if="plugin.siteLoginStatus" class="text-rose-500" title="身份验证失效">
                <AppIcon name="xCircle" class="h-5 w-5" />
              </div>
              <span v-else class="text-muted-foreground/35">—</span>
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-1">
              <!-- Toggle Enable -->
              <Button
                variant="ghost"
                size="icon"
                @click="plugin.enabled ? handleDisable(plugin) : handleEnable(plugin)"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground transition-colors"
                :title="plugin.enabled ? '停用插件' : '启用插件'"
              >
                <AppIcon v-if="plugin.enabled" name="pause" class="h-4 w-4" />
                <AppIcon v-else name="play" class="h-4 w-4 fill-current" />
              </Button>

              <!-- Test Site -->
              <Button
                v-if="plugin.siteName"
                variant="ghost"
                size="icon"
                @click="handleTestSingleBySite(plugin.siteName)"
                :disabled="plugin.siteTesting"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground hover:text-amber-500 transition-colors"
                title="连通性测试"
              >
                <AppIcon name="bolt" class="h-4 w-4" />
              </Button>

              <!-- Login Check -->
              <Button
                v-if="plugin.siteSupportsLogin"
                variant="ghost"
                size="icon"
                @click="handleTestLoginBySite(plugin.siteName)"
                :disabled="plugin.siteLoginTesting"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground hover:text-blue-500 transition-colors"
                title="验证登录状态"
              >
                <AppIcon name="security" class="h-4 w-4" />
              </Button>

              <!-- YouTube OAuth special -->
              <Button
                v-if="plugin.siteName === 'youtube'"
                variant="ghost"
                size="icon"
                @click="plugin.siteOAuthStatus === 'authenticated' || plugin.siteOAuthStatus === 'pending' ? handleRevokeYouTubeOAuth() : handleStartYouTubeOAuth()"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground transition-colors"
                title="授权管理"
              >
                <AppIcon v-if="plugin.siteOAuthStatus === 'authenticated'" name="link" class="h-4 w-4 text-emerald-500" />
                <AppIcon v-else name="unlink" class="h-4 w-4" />
              </Button>

              <!-- Site Config -->
              <Button
                variant="ghost"
                size="icon"
                @click="openSiteEditorByPlugin(plugin)"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                title="站点配置"
              >
                <AppIcon name="settingsPanel" class="h-4 w-4" />
              </Button>

              <!-- Uninstall -->
              <Button
                variant="ghost"
                size="icon"
                @click="handleUninstall(plugin)"
                class="h-8 w-8 rounded-md hover:bg-muted text-muted-foreground hover:text-rose-600 transition-colors"
                title="卸载插件"
              >
                <AppIcon name="trash" class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Site Editor Dialog -->
    <SiteConfigEditorDialog
      :visible="siteEditorVisible"
      :site="editingSite"
      :catalog="siteCatalog"
      :saving="siteEditorSaving"
      :error-message="siteEditorError"
      @close="closeSiteEditor"
      @save="saveSiteEditor"
    />
  </AppPageShell>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue';
import AppEmptyState from '@/components/layout/AppEmptyState.vue';
import AppPageShell from '@/components/layout/AppPageShell.vue';
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue';
import PageHeader from '@/components/layout/PageHeader.vue';
import AppIcon from '@/components/common/AppIcon.vue';
import SiteIcon from '@/components/common/SiteIcon.vue'
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import { Button } from '@/components/ui/button'
import { Logger } from '@/utils/logger'
import { mergeLoginStatusResult, shouldRefreshLoginStatusesAfterCookieImport } from '@/utils/plugin-login-status'
import { useSiteCatalog } from '@/composables/useSites';
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
  uploadSiteCookies,
} from '@/api'

const loading = ref(false);
const installing = ref(false);
const reloading = ref(false);
const plugins = ref([]);
const selectedFile = ref(null);
const actioning = ref(null);
const isInitialLoading = computed(() => loading.value && !plugins.value.length);

const loadingSites = ref(false);
const testingAll = ref(false);
const supportedSites = ref([]);
const connectivityResults = ref([]);
const loginStatusResults = ref({});
const loginStatusTesting = ref({});
const cookieUploading = ref({});
const lastTestedAt = ref(null);
const ytOAuthActioning = ref(false);
let ytOAuthPollTimer = null;

// Site config
const { catalog: siteCatalog, loadCatalog, saveCatalog } = useSiteCatalog();

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

const selectedCookiesFile = ref(null);
const cookiesFileName = ref('');
const importingCookies = ref(false);

const editingSite = ref(null);
const siteEditorVisible = ref(false);
const siteEditorSaving = ref(false);
const siteEditorError = ref('');

const siteCatalogMap = computed(() => siteCatalog.value || {});
const searchQuery = ref('');

const displayPlugins = computed(() => {
  const resultsMap = new Map();
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result);
    });
  }
  const loginResultMap = loginStatusResults.value || {};
  const loginTestingMap = loginStatusTesting.value || {};

  let list = (plugins.value || []).map((plugin) => {
    const primarySite = plugin.sites?.[0] || null;
    const siteName = primarySite?.site_name || primarySite?.name || '';
    const siteResult = resultsMap.get(siteName) || {};
    const loginStatus = loginResultMap[siteName];

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
      cookieUploading: !!cookieUploading.value[siteName],
    };
  });

  if (searchQuery.value.trim()) {
    const keyword = searchQuery.value.trim().toLowerCase();
    list = list.filter(p =>
      p.display_name?.toLowerCase().includes(keyword) ||
      p.plugin_id?.toLowerCase().includes(keyword) ||
      p.description?.toLowerCase().includes(keyword) ||
      p.siteName?.toLowerCase().includes(keyword)
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
    Logger.error('Failed to import cookies', result.error);
  } else if (shouldRefreshLoginStatusesAfterCookieImport(result.data)) {
    if (supportedSites.value.length === 0) await fetchSupportedSites();
    clearLoginStatusCache();
    await testLoginForAllSupportedSites();
    saveResultsToCache();
  }
  importingCookies.value = false;
};

const handleReload = async () => {
  reloading.value = true;
  const res = await reloadPlugins();
  if (!res.error) await fetchPlugins();
  reloading.value = false;
};

const handleEnable = async (plugin) => {
  actioning.value = plugin.plugin_id;
  const res = await enablePlugin(plugin.plugin_id);
  if (!res.error) await fetchPlugins();
  actioning.value = null;
};

const handleDisable = async (plugin) => {
  actioning.value = plugin.plugin_id;
  const res = await disablePlugin(plugin.plugin_id);
  if (!res.error) await fetchPlugins();
  actioning.value = null;
};

const handleUninstall = async (plugin) => {
  if (!confirm(`确定要卸载插件「${plugin.display_name}」吗？`)) return;
  actioning.value = plugin.plugin_id;
  const res = await uninstallPlugin(plugin.plugin_id);
  if (!res.error) await fetchPlugins();
  actioning.value = null;
};

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

const handleTestSingleBySite = async (siteName) => {
  if (!siteName) return;
  const result = await testSiteConnectivity(siteName);
  if (!result.error && result.data) {
    if (connectivityResults.value.length === 0) {
      connectivityResults.value = [{ results: [], summary: { total: 0, accessible: 0, failed: 0, success_rate: 0 } }];
    }
    const results = connectivityResults.value[0].results;
    const existingIndex = results.findIndex(r => r.site_name === siteName);
    if (existingIndex !== -1) results[existingIndex] = result.data;
    else results.push(result.data);
    
    const accessible = results.filter(r => r.accessible).length;
    connectivityResults.value[0].summary = {
      total: results.length,
      accessible,
      failed: results.length - accessible,
      success_rate: results.length > 0 ? Math.round((accessible / results.length) * 100) : 0
    };
    saveResultsToCache();
  }
};

const handleTestLoginBySite = async (siteName) => {
  if (!siteName) return;
  loginStatusTesting.value[siteName] = true;
  try {
    const { data, error } = await testSiteLoginStatus(siteName);
    if (!error && data) upsertLoginStatus(siteName, data);
    else {
      upsertLoginStatus(siteName, {
        site_name: siteName,
        logged_in: false,
        message: error?.message || '检测失败',
        checked_at: new Date().toISOString(),
      });
    }
  } finally {
    loginStatusTesting.value[siteName] = false;
    saveResultsToCache();
  }
};

const upsertLoginStatus = (siteName, payload) => {
  loginStatusResults.value = {
    ...loginStatusResults.value,
    [siteName]: mergeLoginStatusResult(loginStatusResults.value?.[siteName], payload)
  };
};

const openSiteEditorByPlugin = (plugin) => {
  const siteName = plugin.siteName;
  if (!siteName) return;
  const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || {};
  editingSite.value = {
    slug: siteName,
    label: catalogInfo.label || plugin.display_name || siteName,
    enabled: catalogInfo.enabled !== false,
    test_url: catalogInfo.test_url || '',
    domains: catalogInfo.domains || [],
    iconUrl: catalogInfo.icon_url || '',
  };
  siteEditorVisible.value = true;
};

const closeSiteEditor = () => {
  siteEditorVisible.value = false;
  editingSite.value = null;
};

const saveSiteEditor = async ({ slug, sitePayload }) => {
  siteEditorSaving.value = true;
  try {
    await saveCatalog({ [slug]: sitePayload });
    siteEditorVisible.value = false;
  } catch (error) {
    Logger.error('Failed to save site config', error);
  } finally {
    siteEditorSaving.value = false;
  }
};

const fetchPlugins = async () => {
  loading.value = true;
  const { data, error } = await getPlugins();
  if (!error) plugins.value = data || [];
  loading.value = false;
};

const fetchSupportedSites = async () => {
  const { data, error } = await getSupportedSites();
  if (!error && data) supportedSites.value = data.sites || [];
};

const testLoginForAllSupportedSites = async () => {
  const targets = supportedSites.value.filter(site => site.supports_login_status);
  await Promise.all(targets.map(site => handleTestLoginBySite(site.site_name || site.name)));
};

const formatTime = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
};

// YouTube OAuth Handlers
const handleStartYouTubeOAuth = async () => {
  const { data, error } = await setupYouTubeOAuth();
  if (!error && data) {
    if (data.verification_url) window.open(data.verification_url, '_blank');
    if (data.status === 'pending') startYouTubeOAuthPolling();
  }
};

const handleRevokeYouTubeOAuth = async () => {
  await revokeYouTubeOAuth();
  stopYouTubeOAuthPolling();
  fetchPlugins();
};

const startYouTubeOAuthPolling = () => {
  stopYouTubeOAuthPolling();
  ytOAuthPollTimer = setInterval(async () => {
    const { data } = await getYouTubeOAuthStatus();
    if (data?.status !== 'pending') stopYouTubeOAuthPolling();
  }, 3000);
};

const stopYouTubeOAuthPolling = () => {
  if (ytOAuthPollTimer) clearInterval(ytOAuthPollTimer);
  ytOAuthPollTimer = null;
};

onMounted(() => {
  fetchPlugins();
  loadCatalog();
  loadResultsFromCache();
  fetchSupportedSites();
});

onUnmounted(stopYouTubeOAuthPolling);
</script>

<style scoped>
.plugin-page {
  min-height: 100%;
  scrollbar-gutter: stable;
}

.plugin-grid {
  display: grid;
  grid-template-columns: minmax(18rem, 1fr) 100px 180px 100px 100px 200px;
  min-width: 980px;
}
</style>

<template>
  <div class="plugin-page flex h-full flex-col bg-background text-foreground">
    <section class="plugin-shell">
      <div class="toolbar-container">
        <h1 class="plugin-title">插件</h1>
        <div class="plugin-header">
          <div class="plugin-toolbar-right">
            <Button as-child variant="outline" size="xs" class="plugin-toolbar-btn">
              <label>
                <input type="file" accept=".zip" class="hidden" @change="handleFileChange" />
                <CloudArrowUpIcon class="h-3.5 w-3.5" />
                <span>{{ selectedFile ? selectedFile.name : '导入' }}</span>
              </label>
            </Button>
            <Button
              :disabled="!selectedFile || installing"
              @click="handleInstall"
              size="xs"
              class="plugin-toolbar-btn plugin-toolbar-btn--primary"
            >
              <ArrowPathIcon v-if="installing" class="h-3.5 w-3.5 animate-spin" />
              <PlusCircleIcon v-else class="h-3.5 w-3.5" />
            </Button>
            <Button
              :disabled="reloading || loading"
              @click="handleReload"
              size="icon-xs"
              variant="ghost"
              class="plugin-toolbar-icon"
              title="刷新"
            >
              <ArrowPathIcon class="h-3.5 w-3.5" :class="{ 'animate-spin': reloading }" />
            </Button>
            <Button
              @click="handleTestAll"
              :disabled="testingAll || loadingSites"
              size="xs"
              class="plugin-toolbar-btn plugin-toolbar-btn--primary"
            >
              <ArrowPathIcon v-if="testingAll" class="h-3.5 w-3.5 animate-spin" />
              <CheckCircleIcon v-else class="h-3.5 w-3.5" />
              {{ testingAll ? '测试中' : '测试全部' }}
            </Button>
            <Button as-child variant="ghost" size="xs" class="plugin-toolbar-btn">
              <label>
                <input type="file" accept=".txt" class="hidden" @change="handleCookiesFileChange" />
                <span>{{ cookiesFileName || 'Cookie' }}</span>
              </label>
            </Button>
            <Button
              @click="handleImportAllCookies"
              :disabled="!selectedCookiesFile || importingCookies"
              size="xs"
              variant="ghost"
              class="plugin-toolbar-btn"
            >
              {{ importingCookies ? '...' : '导入' }}
            </Button>
            <Button
              @click="handleSyncCookieCloud"
              :disabled="syncingCookieCloud"
              size="xs"
              variant="ghost"
              class="plugin-toolbar-btn"
            >
              {{ syncingCookieCloud ? '...' : '云同步' }}
            </Button>
          </div>
        </div>

        <div class="plugin-stats-row">
          <span class="plugin-stat">
            <span class="plugin-stat__value">{{ pluginSummary.total }}</span>
            <span class="plugin-stat__label">插件</span>
          </span>
          <span class="plugin-stat-sep"></span>
          <span class="plugin-stat">
            <span class="plugin-stat__value text-warning">{{ pluginSummary.attention }}</span>
            <span class="plugin-stat__label">异常</span>
          </span>
          <span class="plugin-stat-sep"></span>
          <span class="plugin-stat">
            <span class="plugin-stat__value">{{ connectivitySummary.total }}</span>
            <span class="plugin-stat__label">站点</span>
          </span>
          <span class="plugin-stat-sep"></span>
          <span class="plugin-stat">
            <span class="plugin-stat__value text-success">{{ connectivitySummary.accessible }}</span>
            <span class="plugin-stat__label">可用</span>
          </span>
          <span class="plugin-stat-sep"></span>
          <span class="plugin-stat">
            <span class="plugin-stat__value text-destructive">{{ connectivitySummary.failed }}</span>
            <span class="plugin-stat__label">异常</span>
          </span>
          <span class="plugin-stat-sep"></span>
          <span class="plugin-stat">
            <span class="plugin-stat__value">{{ connectivitySummary.success_rate }}%</span>
            <span class="plugin-stat__label">成功率</span>
          </span>
          <span v-if="lastTestedAt" class="plugin-timestamp">检测于 {{ formatTime(lastTestedAt) }}</span>
          <div class="plugin-search">
            <MagnifyingGlassIcon class="h-3 w-3" />
            <input
              v-model="searchQuery"
              placeholder="搜索..."
              class="plugin-search-input"
            />
          </div>
        </div>
      </div>
    </section>

    <div class="plugin-content scrollbar-hide flex-grow overflow-y-auto">
      <div class="content-container">
        <div v-if="loading && !plugins.length" class="plugin-loading">
          <div class="animate-spin rounded-full h-6 w-6 border-2 border-muted-foreground/30 border-t-foreground"></div>
        </div>

        <div v-else-if="!loading && !displayPlugins.length" class="plugin-empty">
          <CubeIcon class="h-10 w-10 opacity-20" />
          <p>暂无插件</p>
        </div>

        <div v-else class="plugin-table-wrap">
            <table class="plugin-table">
              <thead>
                <tr>
                  <th class="col-icon"></th>
                  <th class="col-name">名称</th>
                  <th class="col-status">状态</th>
                  <th class="col-caps">能力</th>
                  <th class="col-endpoint">端点</th>
                  <th class="col-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="plugin in displayPlugins" :key="plugin.plugin_id">
                  <td class="col-icon">
                    <SiteIcon
                      v-if="plugin.primarySite"
                      :icon-url="plugin.primarySite.icon_url"
                      :label="plugin.primarySite.site_name || plugin.display_name"
                      size="sm"
                    />
                    <div v-else class="col-icon-placeholder">
                      <CubeIcon class="h-4 w-4 text-muted-foreground/30" />
                    </div>
                  </td>
                  <td class="col-name">
                    <span class="name-primary">{{ plugin.display_name }}</span>
                  </td>
                  <td class="col-status">
                    <span
                      v-if="!plugin.enabled"
                      class="badge badge--off"
                    >停用</span>
                    <span
                      v-else-if="plugin.active_runtime?.state === 'running'"
                      class="badge badge--ok"
                    >运行</span>
                    <span
                      v-else-if="plugin.health?.healthy === false || plugin.active_runtime?.state === 'failed'"
                      class="badge badge--error"
                    >异常</span>
                    <span
                      v-else
                      class="badge badge--loading"
                    >加载中</span>
                  </td>
                  <td class="col-caps">
                    <div class="caps-cell">
                      <span
                        v-for="cap in plugin.capabilities.slice(0, 3)"
                        :key="cap.name"
                        class="cap-tag"
                      >{{ cap.name }}</span>
                      <span v-if="plugin.capabilities.length > 3" class="cap-more">
                        +{{ plugin.capabilities.length - 3 }}
                      </span>
                      <span v-if="!plugin.capabilities.length" class="text-muted-foreground/30">—</span>
                    </div>
                  </td>
                  <td class="col-endpoint">
                    <span class="endpoint-text">{{ plugin.active_runtime?.endpoint || '—' }}</span>
                  </td>
                  <td class="col-actions">
                    <div class="actions-cell">
                      <button
                        v-if="!plugin.enabled"
                        :disabled="actioning === plugin.plugin_id"
                        @click="handleEnable(plugin)"
                        class="action-btn"
                        title="启用"
                      >
                        <PlayIcon class="h-3.5 w-3.5" />
                      </button>
                      <button
                        v-else
                        :disabled="actioning === plugin.plugin_id"
                        @click="handleDisable(plugin)"
                        class="action-btn"
                        title="停用"
                      >
                        <PauseIcon class="h-3.5 w-3.5" />
                      </button>
                      <button
                        :disabled="actioning === plugin.plugin_id"
                        @click="handleUninstall(plugin)"
                        class="action-btn action-btn--danger"
                        title="卸载"
                      >
                        <TrashIcon class="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="plugin-table-sep">
          <div class="plugin-section-divider">
            <span class="plugin-section-label">站点连通性</span>
          </div>
        </div>

        <div v-if="loadingSites && !displaySites.length" class="plugin-loading">
          <div class="animate-spin rounded-full h-6 w-6 border-2 border-muted-foreground/30 border-t-foreground"></div>
        </div>

        <div v-else class="plugin-table-wrap">
          <table class="plugin-table">
            <thead>
              <tr>
                <th class="col-icon"></th>
                <th class="col-name">站点</th>
                <th class="col-domains">域名</th>
                <th class="col-status">网络</th>
                <th class="col-status">登录</th>
                <th class="col-latency">延迟</th>
                <th class="col-actions"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="site in displaySites" :key="site.site_name">
                <td class="col-icon">
                  <SiteIcon
                    :icon-url="site.icon_url"
                    :label="site.display_label || site.site_name || site.name"
                    size="sm"
                  />
                </td>
                <td class="col-name">
                  <span class="name-primary">{{ site.display_label || site.site_name || site.name }}</span>
                    <span
                      v-if="site.config_enabled === false"
                      class="badge badge--off"
                    >禁用</span>
                  </td>
                  <td class="col-domains">
                    <div class="domains-cell">
                      <span
                        v-for="domain in (site.domains || []).slice(0, 3)"
                        :key="domain"
                        class="domain-tag"
                      >{{ domain }}</span>
                      <span v-if="(site.domains || []).length > 3" class="domain-more">
                        +{{ site.domains.length - 3 }}
                      </span>
                      <span v-if="!(site.domains || []).length" class="text-muted-foreground/30">—</span>
                    </div>
                  </td>
                  <td class="col-status">
                    <div v-if="site.testing" class="flex items-center gap-1 text-muted-foreground/40 animate-pulse">
                      <ArrowPathIcon class="h-3 w-3 animate-spin" />
                    </div>
                    <div
                      v-else-if="site.accessible === true"
                      class="status-ok"
                      title="网络可达"
                    >
                      <CheckCircleIcon class="h-3.5 w-3.5" />
                      <span>可达</span>
                    </div>
                    <div
                      v-else-if="site.accessible === false"
                      class="status-error"
                      title="网络不可达"
                    >
                      <XCircleIcon class="h-3.5 w-3.5" />
                      <span>不可达</span>
                    </div>
                    <span v-else class="text-muted-foreground/30">—</span>
                  </td>
                  <td class="col-status">
                    <div v-if="!site.supports_login_status" class="text-muted-foreground/30">—</div>
                    <div v-else-if="site.loginTesting" class="flex items-center gap-1 text-muted-foreground/40 animate-pulse">
                      <ArrowPathIcon class="h-3 w-3 animate-spin" />
                    </div>
                    <div
                      v-else-if="site.loginStatus?.logged_in"
                      class="status-ok"
                      title="登录有效"
                    >
                      <CheckCircleIcon class="h-3.5 w-3.5" />
                      <span>有效</span>
                    </div>
                    <div
                      v-else-if="site.loginStatus"
                      class="status-error"
                      title="登录无效"
                    >
                      <XCircleIcon class="h-3.5 w-3.5" />
                      <span>无效</span>
                    </div>
                    <span v-else class="text-muted-foreground/30">—</span>
                  </td>
                  <td class="col-latency">
                    <span v-if="site.response_time" class="text-xs font-mono" :class="site.response_time > 1000 ? 'text-warning/80' : 'text-muted-foreground/70'">
                      {{ site.response_time }}ms
                    </span>
                    <span v-else class="text-muted-foreground/30">—</span>
                  </td>
                  <td class="col-actions">
                    <div class="actions-cell">
                      <button
                        @click="handleTestSingle(site)"
                        :disabled="site.testing || testingAll"
                        class="action-btn"
                        title="测试"
                      >
                        <BoltIcon class="h-3.5 w-3.5" />
                      </button>
                      <button
                        v-if="site.supports_login_status"
                        @click="handleTestLogin(site)"
                        :disabled="site.loginTesting || testingAll"
                        class="action-btn"
                        title="验证登录"
                      >
                        <KeyIcon class="h-3.5 w-3.5" />
                      </button>
                      <button
                        @click="handleUploadCookies(site)"
                        :disabled="site.cookieUploading || testingAll"
                        class="action-btn"
                        title="上传Cookie"
                      >
                        <CookieIcon class="h-3.5 w-3.5" />
                      </button>
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
  ArrowPathIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  CubeIcon,
  MagnifyingGlassIcon,
  PlusCircleIcon,
  XCircleIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  BoltIcon,
  KeyIcon,
} from '@heroicons/vue/24/outline';
import SiteIcon from '@/components/common/SiteIcon.vue'
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import { Button } from '@/components/ui/button'
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

const loading = ref(false);
const installing = ref(false);
const reloading = ref(false);
const plugins = ref([]);
const selectedFile = ref(null);
const actioning = ref(null);

const loadingSites = ref(false);
const testingAll = ref(false);
const supportedSites = ref([]);
const connectivityResults = ref([]);
const loginStatusResults = ref({});
const loginStatusTesting = ref({});
const cookieUploading = ref({});
const lastTestedAt = ref(null);

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

const getSiteConnectivityBadge = (site) => getConnectivityBadge(site);
const getSiteLoginBadge = (site) => getLoginStatusBadge(site?.loginStatus);

const selectedCookiesFile = ref(null);
const cookiesFileName = ref('');
const importingCookies = ref(false);
const syncingCookieCloud = ref(false);

const { catalog: siteCatalog, loading: siteCatalogLoading, error: siteCatalogErrorState, loadCatalog, saveCatalog } = useSiteCatalog();
const siteCatalogLoaded = ref(false);
const editingSite = ref(null);
const siteEditorVisible = ref(false);
const siteEditorSaving = ref(false);
const siteEditorError = ref('');

const siteCatalogMap = computed(() => siteCatalog.value || {});
const searchQuery = ref('');
const siteSearchQuery = ref('');

const displayPlugins = computed(() => {
  let list = (plugins.value || []).map((plugin) => ({
    ...plugin,
    capabilities: Array.isArray(plugin.capabilities) ? plugin.capabilities : [],
    sites: Array.isArray(plugin.sites) ? plugin.sites : [],
    primarySite: plugin.sites?.[0] || null,
  }));

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

const displaySites = computed(() => {
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

    return {
      ...siteInfo,
      ...result,
      site_name: siteName,
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

const closeSiteEditor = () => {
  siteEditorVisible.value = false;
  editingSite.value = null;
  siteEditorError.value = '';
};

const saveSiteEditor = async ({ slug, sitePayload }) => {
  siteEditorError.value = '';
  siteEditorSaving.value = true;
  try {
    await saveCatalog({
      [slug]: sitePayload,
    });
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
    });
  } catch (error) {
    return value;
  }
};

const fetchSupportedSites = async () => {
  loadingSites.value = true;
  const { data, error } = await getSupportedSites();
  if (!error && data) {
    supportedSites.value = data.sites || [];
  }
  loadingSites.value = false;
};

const handleTestSingle = async (site) => {
  const siteName = site.site_name || site.name;
  const index = displaySites.value.findIndex(s => (s.site_name || s.name) === siteName);
  if (index !== -1) {
    displaySites.value[index].testing = true;
  }

  const result = await testSiteConnectivity(siteName);

  if (!result.error && result.data) {
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
    if (!files.length) return;

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

onMounted(() => {
  fetchPlugins();
  loadSiteCatalog();
  loadResultsFromCache();
  fetchSupportedSites();
});
</script>

<style scoped>
.plugin-page {
  min-height: 100%;
}

.toolbar-container,
.content-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding: 0 2rem;
  }
}

.plugin-shell {
  padding-top: 0.5rem;
}

.plugin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0;
  flex-wrap: wrap;
}

.plugin-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: hsl(var(--foreground));
}

.plugin-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  background: hsl(var(--secondary) / 0.3);
  border-radius: calc(var(--radius-sm) + 2px);
  padding: 2px;
}

.plugin-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: calc(var(--radius-sm) - 1px);
  font-size: 12px;
  font-weight: 500;
  color: hsl(var(--muted-foreground) / 0.7);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.plugin-tab:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--background) / 0.5);
}

.plugin-tab.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  box-shadow: 0 1px 3px hsl(var(--border) / 0.4);
}

.plugin-toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.plugin-toolbar-btn {
  gap: 4px;
  border-radius: calc(var(--radius-sm) - 1px);
}

.plugin-toolbar-btn--primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}

.plugin-toolbar-btn--primary:hover {
  background: hsl(var(--primary) / 0.9);
}

.plugin-toolbar-icon {
  width: 1.75rem;
  height: 1.75rem;
}

.plugin-stats-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
}

.plugin-stat {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.plugin-stat__value {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.plugin-stat__label {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground) / 0.6);
}

.plugin-stat-sep {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: hsl(var(--border));
}

.plugin-timestamp {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground) / 0.4);
  margin-left: auto;
}

.plugin-search {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding: 4px 8px;
  background: hsl(var(--secondary) / 0.3);
  border-radius: calc(var(--radius-sm) - 1px);
  color: hsl(var(--muted-foreground) / 0.5);
}

.plugin-search-input {
  background: transparent;
  border: none;
  outline: none;
  font-size: 12px;
  color: hsl(var(--foreground));
  width: 120px;
}

.plugin-search-input::placeholder {
  color: hsl(var(--muted-foreground) / 0.4);
}

.plugin-content {
  padding-top: 0.5rem;
}

.plugin-loading,
.plugin-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  gap: 1rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
}

/* Section divider */
.plugin-table-sep {
  margin: 1.5rem 0 0.75rem;
}

.plugin-section-divider {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plugin-section-divider::before,
.plugin-section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: hsl(var(--border) / 0.4);
}

.plugin-section-label {
  font-size: 11px;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.6);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* Table */
.plugin-table-wrap {
  overflow-x: auto;
}

.plugin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.plugin-table thead tr {
  border-bottom: 1px solid hsl(var(--border) / 0.5);
}

.plugin-table th {
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.6);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.plugin-table td {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.25);
  vertical-align: middle;
}

.plugin-table tbody tr:hover {
  background: hsl(var(--secondary) / 0.06);
}

.plugin-table tbody tr:last-child td {
  border-bottom: none;
}

/* Column widths */
.col-icon { width: 2.5rem; text-align: center; }
.col-name { min-width: 160px; }
.col-status { min-width: 70px; }
.col-caps { min-width: 120px; }
.col-endpoint { min-width: 180px; }
.col-latency { width: 70px; text-align: center; }
.col-actions { width: 90px; text-align: right; }

/* Cell styles */
.name-primary {
  font-weight: 600;
  color: hsl(var(--foreground));
}

.caps-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cap-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

.cap-more {
  font-size: 10px;
  color: hsl(var(--muted-foreground) / 0.4);
}

.endpoint-text {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: hsl(var(--muted-foreground) / 0.5);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
  display: block;
}

.col-icon-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Badge */
.badge {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.03em;
}

.badge--ok {
  color: hsl(var(--foreground));
}

.badge--error {
  color: hsl(var(--foreground));
}

.badge--off {
  color: hsl(var(--muted-foreground));
}

.badge--loading {
  color: hsl(var(--muted-foreground));
}

/* Status */
.status-ok,
.status-error {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-ok {
  color: hsl(var(--success));
}

.status-error {
  color: hsl(var(--destructive));
}

/* Actions */
.actions-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  background: transparent;
  border-radius: calc(var(--radius-sm) - 1px);
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: hsl(var(--secondary) / 0.4);
  color: hsl(var(--foreground));
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.3;
}

.action-btn--danger:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

/* Responsive */
@media (max-width: 768px) {
  .plugin-header {
    flex-direction: column;
    align-items: stretch;
  }

  .plugin-toolbar-right {
    justify-content: flex-end;
  }

  .col-endpoint,
  .col-caps {
    display: none;
  }
}
</style>

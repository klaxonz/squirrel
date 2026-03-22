<template>
  <div class="plugin-manager bg-background text-foreground h-full flex flex-col min-h-0">
    <div class="toolbar-container pt-6 pb-4">
      <div class="plugin-hero">
        <div class="plugin-hero__copy">
          <span class="plugin-eyebrow">extension control room</span>
          <h1 class="plugin-hero__title">插件管理</h1>
          <p class="plugin-hero__description">管理扩展资产与站点连通性，让插件状态、Cookie、登录检测和可访问性落在一套清晰的运营视图里。</p>
        </div>
        <div class="plugin-hero__controls">
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
              <label class="plugin-pill-button cursor-pointer">
                <input
                  type="file"
                  accept=".zip"
                  class="hidden"
                  @change="handleFileChange"
                />
                <CloudArrowUpIcon class="w-5 h-5" />
                <span class="text-sm font-medium">{{ selectedFile ? selectedFile.name : '选择文件' }}</span>
              </label>
              <button
                class="plugin-primary-action"
                :disabled="!selectedFile || installing"
                @click="handleInstall"
              >
                {{ installing ? '安装中...' : '导入插件' }}
              </button>
              <button
                class="plugin-pill-icon"
                :disabled="reloading || loading"
                @click="handleReload"
                title="重新加载插件"
              >
                <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': reloading }" />
              </button>
            </template>
            <template v-else>
              <label class="plugin-pill-button cursor-pointer text-xs md:text-sm">
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
              <button
                @click="handleImportAllCookies"
                :disabled="!selectedCookiesFile || importingCookies"
                class="plugin-pill-button text-xs md:text-sm"
              >
                {{ importingCookies ? '导入中...' : '导入所有站点 Cookie' }}
              </button>
              <button
                @click="handleSyncCookieCloud"
                :disabled="syncingCookieCloud"
                class="plugin-pill-button text-xs md:text-sm"
              >
                {{ syncingCookieCloud ? '同步中...' : '从 CookieCloud 同步' }}
              </button>
              <button
                @click="handleTestAll"
                :disabled="testingAll || loadingSites"
                class="plugin-primary-action flex items-center gap-2"
              >
                <ArrowPathIcon v-if="testingAll" class="w-4 h-4 animate-spin" />
                <CheckCircleIcon v-else class="w-4 h-4" />
                {{ testingAll ? '测试中...' : '测试全部' }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div class="content-container pb-10 flex-1 min-h-0 space-y-6">
      <div v-if="currentTab === 'plugins'" class="space-y-4">
        <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Card class="plugin-summary-card">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">总插件数</p>
              <p class="plugin-summary-card__value">{{ pluginSummary.total }}</p>
            </CardContent>
          </Card>
          <Card class="plugin-summary-card plugin-summary-card--accent">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">已启用</p>
              <p class="plugin-summary-card__value text-success">{{ pluginSummary.enabled }}</p>
            </CardContent>
          </Card>
          <Card class="plugin-summary-card">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">外部来源</p>
              <p class="plugin-summary-card__value">{{ pluginSummary.external }}</p>
            </CardContent>
          </Card>
        </div>

        <div v-if="loading" class="plugin-loading-shell flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-foreground"></div>
        </div>

        <div v-else-if="plugins.length === 0" class="plugin-loading-shell flex flex-col items-center justify-center py-20 text-muted-foreground">
          <CubeIcon class="w-16 h-16 mb-4 opacity-40" />
          <p class="text-sm">暂无插件</p>
          <p class="text-xs mt-1">请导入插件 ZIP 包</p>
        </div>

        <div v-else class="plugin-table-shell overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="plugin-table-shell__thead">
                <tr class="border-b border-border">
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">名称</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">版本</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">来源</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground hidden lg:table-cell">描述</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-muted-foreground">状态</th>
                  <th class="text-right py-3 px-4 text-sm font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="plugin in plugins"
                  :key="plugin.name"
                  class="plugin-table-shell__row border-b border-border"
                >
                  <td class="py-4 px-4">
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="font-medium">{{ plugin.name }}</span>
                        <span v-if="pluginBadgeLabel(plugin)" class="plugin-tag" :class="getPluginBadgeClass(plugin)">
                          {{ pluginBadgeLabel(plugin) }}
                        </span>
                      </div>
                      <div v-if="plugin.module" class="text-xs text-muted-foreground mt-0.5">{{ plugin.module }}</div>
                    </div>
                  </td>
                  <td class="py-4 px-4 text-muted-foreground text-sm">{{ plugin.version || '—' }}</td>
                  <td class="py-4 px-4 text-muted-foreground text-sm">{{ formatSource(plugin.source) }}</td>
                  <td class="py-4 px-4 text-muted-foreground text-sm hidden lg:table-cell max-w-md">
                    <div class="line-clamp-2">{{ plugin.description || '暂无描述' }}</div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex justify-center">
                      <span class="plugin-tag" :class="plugin.enabled ? 'plugin-tag--success' : 'plugin-tag--muted'">
                        {{ plugin.enabled ? '已启用' : '已禁用' }}
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        v-if="!plugin.enabled"
                        class="plugin-inline-action"
                        :disabled="actioning === plugin.name || plugin.state === 'missing'"
                        @click="handleEnable(plugin)"
                      >
                        启用
                      </button>
                      <button
                        v-if="plugin.enabled"
                        class="plugin-inline-action"
                        :disabled="actioning === plugin.name || plugin.state === 'missing'"
                        @click="handleDisable(plugin)"
                      >
                        禁用
                      </button>
                      <button
                        v-if="plugin.source === 'external'"
                        class="plugin-inline-action plugin-inline-action--danger"
                        :disabled="actioning === plugin.name"
                        @click="handleUninstall(plugin)"
                      >
                        卸载
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="currentTab === 'connectivity'" class="space-y-4">
        <div v-if="connectivityResults.length > 0" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Card class="plugin-summary-card">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">总站点数</p>
              <p class="plugin-summary-card__value text-foreground">{{ connectivitySummary.total }}</p>
            </CardContent>
          </Card>
          <Card class="plugin-summary-card plugin-summary-card--accent">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">可访问</p>
              <p class="plugin-summary-card__value text-success">{{ connectivitySummary.accessible }}</p>
            </CardContent>
          </Card>
          <Card class="plugin-summary-card">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">不可访问</p>
              <p class="plugin-summary-card__value text-destructive">{{ connectivitySummary.failed }}</p>
            </CardContent>
          </Card>
          <Card class="plugin-summary-card">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">成功率</p>
              <p class="plugin-summary-card__value text-success">{{ connectivitySummary.success_rate }}%</p>
            </CardContent>
          </Card>
        </div>

        <div v-if="lastTestedAt" class="plugin-last-tested">
          上次全量检测：{{ formatTime(lastTestedAt) }}
        </div>

        <div v-if="loadingSites" class="plugin-loading-shell flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-2 border-muted-foreground/30 border-t-foreground"></div>
        </div>

        <div v-else class="plugin-table-shell overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="plugin-table-shell__thead">
                <tr class="border-b border-border">
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">站点名称</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground hidden lg:table-cell">支持域名</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-muted-foreground">状态</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-muted-foreground">登录状态</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-muted-foreground">响应时间</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-muted-foreground hidden md:table-cell">IP地址</th>
                  <th class="text-right py-3 px-4 text-sm font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="site in displaySites"
                  :key="site.site_name"
                  class="plugin-table-shell__row border-b border-border"
                >
                  <td class="py-4 px-4">
                    <div class="font-medium flex items-center gap-2">
                      <span>{{ site.display_label || site.site_name || site.name }}</span>
                      <span
                        v-if="site.config_enabled === false"
                        class="plugin-tag plugin-tag--danger"
                      >
                        已禁用
                      </span>
                    </div>
                    <div class="text-xs text-muted-foreground mt-0.5">
                      标识：{{ site.site_name || site.name }}
                    </div>
                    <div v-if="site.test_url" class="text-xs text-muted-foreground mt-0.5">{{ site.test_url }}</div>
                  </td>
                  <td class="py-4 px-4 hidden lg:table-cell">
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="domain in site.domains?.slice(0, 3) || []"
                        :key="domain"
                        class="plugin-tag plugin-tag--muted"
                      >
                        {{ domain }}
                      </span>
                      <span
                        v-if="site.domains?.length > 3"
                        class="plugin-tag plugin-tag--muted"
                      >
                        +{{ site.domains.length - 3 }}
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex justify-center">
                      <span v-if="site.testing" class="plugin-tag plugin-tag--info flex items-center gap-1">
                        <ArrowPathIcon class="w-3 h-3 animate-spin" />
                        测试中
                      </span>
                      <span v-else-if="site.accessible === true" class="plugin-tag plugin-tag--success">
                        ✓ 可访问
                      </span>
                      <span
                        v-else-if="site.accessible === false"
                        class="plugin-tag plugin-tag--danger"
                        :title="site.error_message"
                      >
                        ✗ 不可访问
                      </span>
                      <span v-else class="plugin-tag plugin-tag--muted">
                        未测试
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex justify-center">
                      <span v-if="!site.supports_login_status" class="plugin-tag plugin-tag--muted">
                        未接入
                      </span>
                      <span v-else-if="site.loginTesting" class="plugin-tag plugin-tag--info flex items-center gap-1">
                        <ArrowPathIcon class="w-3 h-3 animate-spin" />
                        检测中
                      </span>
                      <span
                        v-else-if="site.loginStatus?.logged_in"
                        class="plugin-tag plugin-tag--success"
                        :title="site.loginStatus?.message || '已登录'"
                      >
                        已登录
                      </span>
                      <span
                        v-else-if="site.loginStatus"
                        class="plugin-tag plugin-tag--danger"
                        :title="site.loginStatus?.message || '未登录'"
                      >
                        未登录
                      </span>
                      <span v-else class="plugin-tag plugin-tag--muted">
                        未检测
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4 text-center text-sm text-muted-foreground">
                    {{ site.response_time ? `${site.response_time}ms` : '—' }}
                  </td>
                  <td class="py-4 px-4 text-center text-sm text-muted-foreground hidden md:table-cell">
                    {{ site.ip_address || '—' }}
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        @click="handleTestSingle(site)"
                        :disabled="site.testing || testingAll"
                        class="plugin-inline-action"
                      >
                        {{ site.testing ? '测试中...' : '连通性' }}
                      </button>
                      <button
                        v-if="site.supports_login_status"
                        @click="handleTestLogin(site)"
                        :disabled="site.loginTesting || testingAll"
                        class="plugin-inline-action"
                      >
                        {{ site.loginTesting ? '检测中...' : '登录检测' }}
                      </button>
                      <button
                        @click="handleUploadCookies(site)"
                        :disabled="site.cookieUploading || testingAll"
                        class="plugin-inline-action"
                      >
                        {{ site.cookieUploading ? '上传中...' : '上传Cookie' }}
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
  CloudArrowUpIcon,
  ArrowPathIcon,
  CubeIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline';
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import { Card, CardContent } from '@/components/ui/card';
import { Logger } from '@/utils/logger'
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

const pluginSummary = computed(() => ({
  total: plugins.value.length,
  enabled: plugins.value.filter(plugin => plugin.enabled).length,
  external: plugins.value.filter(plugin => plugin.source === 'external').length,
}));

const connectivitySummary = computed(() => {
  if (connectivityResults.value.length === 0) {
    return { total: 0, accessible: 0, failed: 0, success_rate: 0 };
  }
  return connectivityResults.value[0]?.summary || { total: 0, accessible: 0, failed: 0, success_rate: 0 };
});

const pluginBadgeLabel = (plugin) => {
  if (plugin.state === 'missing') return '配置缺失';
  if (plugin.source === 'external') return '外部';
  if (plugin.source === 'internal') return '内置';
  return '';
};

const getPluginBadgeClass = (plugin) => {
  if (plugin.state === 'missing') return 'plugin-tag--danger';
  if (plugin.source === 'external') return 'plugin-tag--info';
  if (plugin.source === 'internal') return 'plugin-tag--warning';
  return 'plugin-tag--muted';
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

  return supportedSites.value.map(siteInfo => {
    const siteName = siteInfo.name;
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
      loginStatus: loginResultMap[siteName],
      loginTesting: !!loginTestingMap[siteName],
      supports_login_status: siteInfo.supports_login_status ?? false,
      cookieUploading: !!cookieUploading.value[siteName],
      display_label: displayLabel,
      config_enabled: catalogInfo?.enabled !== false,
      config_aliases: catalogInfo?.aliases || [],
    };
  });
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
    [siteName]: payload
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
  actioning.value = plugin.name;
  const res = await enablePlugin(plugin.name);
  if (!res.error) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const handleDisable = async (plugin) => {
  actioning.value = plugin.name;
  const res = await disablePlugin(plugin.name);
  if (!res.error) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const handleUninstall = async (plugin) => {
  actioning.value = plugin.name;
  const res = await uninstallPlugin(plugin.name);
  if (!res.error) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const formatSource = (source) => {
  switch (source) {
    case 'external':
      return '外部目录';
    case 'internal':
      return '内置插件';
    case 'package':
      return '环境安装';
    case 'missing':
      return '配置缺失';
    default:
      return '未知';
  }
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
        loginStatusResults.value = {
          ...loginStatusResults.value,
          [siteName]: result.data.login_status
        };
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
  padding-left: 1rem;
  padding-right: 1rem;
  width: 100%;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.plugin-hero,
.plugin-summary-card,
.plugin-loading-shell,
.plugin-table-shell,
.plugin-last-tested {
  border: 1px solid hsl(var(--border) / 0.76);
  background: linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
  box-shadow: 0 20px 52px hsl(var(--foreground) / 0.045);
}

.plugin-hero {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem;
  border-radius: 1.75rem;
  background:
    radial-gradient(circle at top left, hsl(var(--primary) / 0.14), transparent 34%),
    radial-gradient(circle at bottom right, hsl(var(--accent) / 0.8), transparent 38%),
    linear-gradient(135deg, hsl(var(--card)), hsl(var(--card) / 0.94));
}

.plugin-eyebrow,
.plugin-summary-card__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: hsl(var(--muted-foreground));
}

.plugin-hero__title {
  margin-top: 0.6rem;
  font-size: clamp(1.95rem, 2vw, 2.55rem);
  line-height: 1.05;
  font-weight: 600;
}

.plugin-hero__description {
  margin-top: 0.75rem;
  max-width: 44rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.7;
  font-size: 0.95rem;
}

.plugin-hero__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.plugin-hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.plugin-tab-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background) / 0.72);
}

.plugin-tab-switch__button {
  padding: 0.7rem 1rem;
  border-radius: 999px;
  color: hsl(var(--muted-foreground));
  font-size: 0.9rem;
  font-weight: 500;
  transition: background-color 160ms ease, color 160ms ease, box-shadow 160ms ease;
}

.plugin-tab-switch__button:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.plugin-tab-switch__button--active {
  background: hsl(var(--card));
  color: hsl(var(--foreground));
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.08);
}

.plugin-pill-button,
.plugin-pill-icon,
.plugin-primary-action,
.plugin-inline-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  min-height: 2.75rem;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--foreground));
  transition: background-color 160ms ease, transform 160ms ease, opacity 160ms ease;
}

.plugin-pill-button:hover,
.plugin-pill-icon:hover,
.plugin-inline-action:hover {
  background: hsl(var(--accent));
}

.plugin-pill-icon {
  width: 2.75rem;
  padding-inline: 0;
}

.plugin-primary-action {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary) / 0.32);
  box-shadow: 0 16px 36px hsl(var(--primary) / 0.18);
}

.plugin-primary-action:hover:not(:disabled) {
  transform: translateY(-1px);
}

.plugin-inline-action {
  min-height: 2.1rem;
  padding: 0.45rem 0.9rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.plugin-inline-action--danger:hover {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.plugin-primary-action:disabled,
.plugin-pill-button:disabled,
.plugin-pill-icon:disabled,
.plugin-inline-action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.plugin-summary-card {
  overflow: hidden;
}

.plugin-summary-card--accent {
  background:
    radial-gradient(circle at top left, hsl(var(--primary) / 0.14), transparent 35%),
    linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
}

.plugin-summary-card__value {
  margin-top: 0.8rem;
  font-size: 1.85rem;
  line-height: 1;
  font-weight: 600;
}

.plugin-loading-shell,
.plugin-table-shell {
  border-radius: 1.5rem;
}

.plugin-table-shell__thead {
  background: linear-gradient(180deg, hsl(var(--background) / 0.96), hsl(var(--card) / 0.92));
}

.plugin-table-shell__row {
  transition: background-color 160ms ease;
}

.plugin-table-shell__row:hover {
  background: hsl(var(--accent) / 0.58);
}

.plugin-last-tested {
  display: inline-flex;
  align-items: center;
  padding: 0.7rem 1rem;
  border-radius: 999px;
  font-size: 0.8rem;
  color: hsl(var(--muted-foreground));
}

.plugin-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 0.68rem;
  font-weight: 600;
}

.plugin-tag--muted {
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
  border-color: hsl(var(--border));
}

.plugin-tag--info {
  background: hsl(var(--info) / 0.12);
  color: hsl(var(--info));
  border-color: hsl(var(--info) / 0.22);
}

.plugin-tag--warning {
  background: hsl(var(--warning) / 0.12);
  color: hsl(var(--warning));
  border-color: hsl(var(--warning) / 0.22);
}

.plugin-tag--success {
  background: hsl(var(--success) / 0.12);
  color: hsl(var(--success));
  border-color: hsl(var(--success) / 0.22);
}

.plugin-tag--danger {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
  border-color: hsl(var(--destructive) / 0.24);
}

@media (min-width: 1024px) {
  .plugin-hero {
    padding: 1.75rem;
  }
}

</style>

<template>
  <AppPageShell class="plugin-page">
    <section class="plugin-shell">
      <AppToolbarFrame class="toolbar-container">
        <div class="plugin-header">
          <div v-if="isInitialLoading" class="plugin-toolbar-skeleton" aria-hidden="true">
            <div
              v-for="(width, index) in toolbarSkeletonWidths"
              :key="`${width}-${index}`"
              class="plugin-toolbar-skeleton__chip skeleton-surface"
              :style="{ width }"
            ></div>
          </div>
          <div v-else class="plugin-toolbar-right">
            <Button as-child variant="outline" size="xs" class="plugin-toolbar-btn plugin-toolbar-btn--quiet">
              <label>
                <input type="file" accept=".zip" class="hidden" @change="handleFileChange" />
                <CloudArrowUpIcon class="h-3.5 w-3.5" />
                <span>{{ selectedFile ? selectedFile.name : '导入插件' }}</span>
              </label>
            </Button>
            <Button
              v-if="selectedFile"
              :disabled="!selectedFile || installing"
              @click="handleInstall"
              size="xs"
              class="plugin-toolbar-btn plugin-toolbar-btn--primary"
            >
              <ArrowPathIcon v-if="installing" class="h-3.5 w-3.5 animate-spin" />
              <PlusCircleIcon v-else class="h-3.5 w-3.5" />
              {{ installing ? '安装中' : '安装' }}
            </Button>
            <Button as-child variant="outline" size="xs" class="plugin-toolbar-btn plugin-toolbar-btn--quiet">
              <label>
                <input type="file" accept=".txt,.json" class="hidden" @change="handleCookiesFileChange" />
                <CloudArrowUpIcon class="h-3.5 w-3.5" />
                <span>{{ cookiesFileName || '导入 Cookie' }}</span>
              </label>
            </Button>
            <Button
              v-if="selectedCookiesFile"
              @click="handleImportAllCookies"
              :disabled="!selectedCookiesFile || importingCookies"
              size="xs"
              class="plugin-toolbar-btn plugin-toolbar-btn--primary"
            >
              <ArrowPathIcon v-if="importingCookies" class="h-3.5 w-3.5 animate-spin" />
              <PlusCircleIcon v-else class="h-3.5 w-3.5" />
              {{ importingCookies ? '导入中' : '导入' }}
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
          </div>
        </div>

        <div class="plugin-stats-row">
          <template v-if="isInitialLoading">
            <div
              v-for="(item, index) in statSkeletonItems"
              :key="`stat-${index}`"
              class="plugin-stat-skeleton"
              aria-hidden="true"
            >
              <span class="plugin-stat-skeleton__value skeleton-surface" :style="{ width: item.valueWidth }"></span>
              <span class="plugin-stat-skeleton__label skeleton-surface" :style="{ width: item.labelWidth }"></span>
            </div>
            <span class="plugin-timestamp plugin-timestamp--skeleton skeleton-surface" aria-hidden="true"></span>
            <div class="plugin-search plugin-search--skeleton" aria-hidden="true">
              <span class="plugin-search__icon-skeleton skeleton-surface"></span>
              <span class="plugin-search__input-skeleton skeleton-surface"></span>
            </div>
            <span class="plugin-search-refresh plugin-search-refresh--skeleton skeleton-surface" aria-hidden="true"></span>
          </template>
          <template v-else>
            <span class="plugin-stat">
              <span class="plugin-stat__value">{{ pluginSummary.total }}</span>
              <span class="plugin-stat__label">已安装</span>
            </span>
            <span class="plugin-stat-sep"></span>
            <span class="plugin-stat">
              <span class="plugin-stat__value text-success">{{ pluginSummary.running }}</span>
              <span class="plugin-stat__label">运行中</span>
            </span>
            <template v-if="pluginSummary.attention > 0">
              <span class="plugin-stat-sep"></span>
              <span class="plugin-stat">
                <span class="plugin-stat__value text-warning">{{ pluginSummary.attention }}</span>
                <span class="plugin-stat__label">需关注</span>
              </span>
            </template>
            <template v-if="connectivitySummary.total > 0">
              <span class="plugin-stat-sep"></span>
              <span class="plugin-stat">
                <span class="plugin-stat__value">{{ connectivitySummary.accessible }}/{{ connectivitySummary.total }}</span>
                <span class="plugin-stat__label">已检测</span>
              </span>
            </template>
            <span v-if="lastTestedAt" class="plugin-timestamp">最近检测 {{ formatTime(lastTestedAt) }}</span>
            <div class="plugin-search">
              <MagnifyingGlassIcon class="h-3 w-3" />
              <input
                v-model="searchQuery"
                placeholder="搜索..."
                class="plugin-search-input"
              />
            </div>
            <Button
              :disabled="reloading || loading"
              @click="handleReload"
              size="icon-xs"
              variant="ghost"
              class="plugin-search-refresh"
              title="刷新"
            >
              <ArrowPathIcon class="h-3.5 w-3.5" :class="{ 'animate-spin': reloading }" />
            </Button>
          </template>
        </div>
      </AppToolbarFrame>
    </section>

    <div class="plugin-content scrollbar-hide flex-grow overflow-y-auto">
      <div class="content-container">
        <div v-if="isInitialLoading" class="plugin-skeleton-wrap plugin-table-wrap">
          <table class="plugin-table">
            <thead>
              <tr>
                <th class="col-icon"></th>
                <th class="col-name">名称</th>
                <th class="col-status">状态</th>
                <th class="col-caps">能力</th>
                <th class="col-endpoint">端点</th>
                <th class="col-site-access">网络</th>
                <th class="col-site-login">登录</th>
                <th class="col-actions"></th>
              </tr>
            </thead>
            <tbody>
              <PluginSkeleton
                v-for="(row, index) in pluginSkeletonRows"
                :key="`plugin-skeleton-${index}`"
                :delay="index * 60"
                :name-width="row.nameWidth"
                :meta-width="row.metaWidth"
                :status-width="row.statusWidth"
                :caps="row.caps"
                :endpoint-width="row.endpointWidth"
                :network-width="row.networkWidth"
                :login-width="row.loginWidth"
                :actions="row.actions"
              />
            </tbody>
          </table>
        </div>

        <AppEmptyState
          v-else-if="!displayPlugins.length"
          class="plugin-empty-state"
          eyebrow="插件管理"
          :title="searchQuery ? '没有匹配的插件' : '还没有可展示的插件'"
          :copy="searchQuery ? '尝试更换搜索关键词。' : '导入插件后，会在这里显示运行状态、能力和站点配置。'"
        />

        <div v-else class="plugin-table-wrap">
          <table class="plugin-table">
            <thead>
              <tr>
                <th class="col-icon"></th>
                <th class="col-name">名称</th>
                <th class="col-status">状态</th>
                <th class="col-caps">能力</th>
                <th class="col-endpoint">端点</th>
                <th class="col-site-access">网络</th>
                <th class="col-site-login">登录</th>
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
                  <span v-if="!plugin.capabilities.length" class="text-muted-foreground/30">—</span>
                  <span v-else class="caps-inline">
                    <span
                      v-for="(cap, idx) in plugin.capabilities.slice(0, 2)"
                      :key="cap.name"
                      class="cap-wrapper"
                    >
                      <span class="cap-tag">{{ cap.name }}</span>
                      <span class="cap-tooltip">{{ plugin.capabilities.map(c => c.name).join('\n') }}</span>
                      <span v-if="idx < Math.min(plugin.capabilities.length, 2) - 1"> </span>
                    </span>
                    <span v-if="plugin.capabilities.length > 2" class="cap-wrapper">
                      <span class="cap-more" :data-count="plugin.capabilities.length - 2">
                        +{{ plugin.capabilities.length - 2 }}
                      </span>
                      <span class="cap-tooltip">{{ plugin.capabilities.map(c => c.name).join('\n') }}</span>
                    </span>
                  </span>
                </td>
                <td class="col-endpoint">
                  <span class="endpoint-text">{{ plugin.active_runtime?.endpoint || '—' }}</span>
                </td>
                <td class="col-site-access">
                  <div v-if="plugin.siteTesting" class="flex items-center gap-1 text-muted-foreground/40 animate-pulse">
                    <ArrowPathIcon class="h-3 w-3 animate-spin" />
                  </div>
                  <div
                    v-else-if="plugin.siteAccessible === true"
                    class="status-ok"
                    title="网络可达"
                  >
                    <CheckCircleIcon class="h-3.5 w-3.5" />
                    <span>可达</span>
                  </div>
                  <div
                    v-else-if="plugin.siteAccessible === false"
                    class="status-error"
                    title="网络不可达"
                  >
                    <XCircleIcon class="h-3.5 w-3.5" />
                    <span>不可达</span>
                  </div>
                  <span v-else class="text-muted-foreground/30">—</span>
                </td>
                <td class="col-site-login">
                  <div v-if="plugin.siteLoginTesting" class="flex items-center gap-1 text-muted-foreground/40 animate-pulse">
                    <ArrowPathIcon class="h-3 w-3 animate-spin" />
                  </div>
                  <div
                    v-else-if="plugin.siteOAuthStatus === 'authenticated'"
                    class="status-ok"
                    :title="plugin.siteOAuthAccount?.email || 'YouTube OAuth 已连接'"
                  >
                    <LinkIcon class="h-3.5 w-3.5" />
                    <span>已授权</span>
                  </div>
                  <div
                    v-else-if="plugin.siteOAuthStatus === 'pending'"
                    class="status-warning"
                    :title="plugin.siteLoginStatus?.user_code ? `等待完成授权，验证码：${plugin.siteLoginStatus.user_code}` : '等待完成浏览器授权'"
                  >
                    <ArrowPathIcon class="h-3.5 w-3.5 animate-spin" />
                    <span>待授权</span>
                  </div>
                  <div
                    v-else-if="plugin.siteOAuthStatus === 'expired'"
                    class="status-warning"
                    title="YouTube OAuth 已过期"
                  >
                    <XCircleIcon class="h-3.5 w-3.5" />
                    <span>已过期</span>
                  </div>
                  <div
                    v-else-if="plugin.siteOAuthStatus === 'error'"
                    class="status-error"
                    :title="plugin.siteLoginStatus?.message || 'YouTube OAuth 异常'"
                  >
                    <XCircleIcon class="h-3.5 w-3.5" />
                    <span>异常</span>
                  </div>
                  <div
                    v-else-if="plugin.siteLoginStatus?.logged_in"
                    class="status-ok"
                    title="登录有效"
                  >
                    <CheckCircleIcon class="h-3.5 w-3.5" />
                    <span>有效</span>
                  </div>
                  <div
                    v-else-if="plugin.siteLoginStatus"
                    class="status-error"
                    title="登录无效"
                  >
                    <XCircleIcon class="h-3.5 w-3.5" />
                    <span>无效</span>
                  </div>
                  <span v-else class="text-muted-foreground/30">—</span>
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
                      v-if="plugin.siteName"
                      @click="handleTestSingleBySite(plugin.siteName)"
                      :disabled="plugin.siteTesting || testingAll"
                      class="action-btn"
                      title="测试"
                    >
                      <BoltIcon class="h-3.5 w-3.5" />
                    </button>
                    <button
                      v-if="plugin.siteSupportsLogin"
                      @click="handleTestLoginBySite(plugin.siteName)"
                      :disabled="plugin.siteLoginTesting || testingAll"
                      class="action-btn"
                      title="验证登录"
                    >
                      <KeyIcon class="h-3.5 w-3.5" />
                    </button>
                    <button
                      v-if="plugin.siteName === 'youtube'"
                      @click="plugin.siteOAuthStatus === 'authenticated' || plugin.siteOAuthStatus === 'pending' ? handleRevokeYouTubeOAuth() : handleStartYouTubeOAuth()"
                      :disabled="ytOAuthActioning || testingAll"
                      class="action-btn"
                      :title="plugin.siteOAuthStatus === 'authenticated' || plugin.siteOAuthStatus === 'pending' ? '解除 YouTube 授权' : '关联 YouTube 账户'"
                    >
                      <ArrowPathIcon v-if="ytOAuthActioning" class="h-3.5 w-3.5 animate-spin" />
                      <LinkSlashIcon
                        v-else-if="plugin.siteOAuthStatus === 'authenticated' || plugin.siteOAuthStatus === 'pending'"
                        class="h-3.5 w-3.5"
                      />
                      <LinkIcon v-else class="h-3.5 w-3.5" />
                    </button>
                    <button
                      v-if="plugin.siteName"
                      @click="handleUploadCookiesBySite(plugin.siteName)"
                      :disabled="plugin.cookieUploading || testingAll"
                      class="action-btn"
                      title="上传Cookie"
                    >
                      <CookieIcon class="h-3.5 w-3.5" />
                    </button>
                    <button
                      @click="openSiteEditorByPlugin(plugin)"
                      class="action-btn"
                      title="站点配置"
                    >
                      <CogIcon class="h-3.5 w-3.5" />
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
  </AppPageShell>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue';
import AppEmptyState from '@/components/layout/AppEmptyState.vue';
import AppPageShell from '@/components/layout/AppPageShell.vue';
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  CogIcon,
  CubeIcon,
  MagnifyingGlassIcon,
  PlusCircleIcon,
  XCircleIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  BoltIcon,
  KeyIcon,
  LinkIcon,
  LinkSlashIcon,
} from '@heroicons/vue/24/outline';
import SiteIcon from '@/components/common/SiteIcon.vue'
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import PluginSkeleton from '@/components/settings/PluginSkeleton.vue';
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

const toolbarSkeletonWidths = ['8.5rem', '8.5rem', '5.5rem'];
const statSkeletonItems = [
  { valueWidth: '1.5rem', labelWidth: '2rem' },
  { valueWidth: '1.5rem', labelWidth: '2rem' },
  { valueWidth: '1.6rem', labelWidth: '2rem' },
  { valueWidth: '2.5rem', labelWidth: '2rem' },
];
const pluginSkeletonRows = [
  {
    nameWidth: '8.5rem',
    metaWidth: '5rem',
    statusWidth: '3rem',
    caps: ['2.5rem', '3.25rem'],
    endpointWidth: '8.5rem',
    networkWidth: '2.5rem',
    loginWidth: '3rem',
    actions: 6,
  },
  {
    nameWidth: '7rem',
    metaWidth: '4.25rem',
    statusWidth: '3.5rem',
    caps: ['3rem', '2.25rem', '2rem'],
    endpointWidth: '7rem',
    networkWidth: '2.75rem',
    loginWidth: '2.5rem',
    actions: 5,
  },
  {
    nameWidth: '9rem',
    metaWidth: '5.75rem',
    statusWidth: '2.75rem',
    caps: ['2.75rem'],
    endpointWidth: '9.5rem',
    networkWidth: '3rem',
    loginWidth: '3.5rem',
    actions: 6,
  },
  {
    nameWidth: '7.75rem',
    metaWidth: '4.75rem',
    statusWidth: '3.25rem',
    caps: ['3.25rem', '2.5rem'],
    endpointWidth: '7.5rem',
    networkWidth: '2.5rem',
    loginWidth: '2.75rem',
    actions: 4,
  },
  {
    nameWidth: '8.25rem',
    metaWidth: '5.25rem',
    statusWidth: '3rem',
    caps: ['2.75rem', '2.75rem', '2rem'],
    endpointWidth: '8rem',
    networkWidth: '2.75rem',
    loginWidth: '3rem',
    actions: 6,
  },
  {
    nameWidth: '6.75rem',
    metaWidth: '4rem',
    statusWidth: '2.75rem',
    caps: ['2.25rem', '3rem'],
    endpointWidth: '6.5rem',
    networkWidth: '2.25rem',
    loginWidth: '2.75rem',
    actions: 5,
  },
];

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
  // Build maps for site connectivity and catalog info
  const resultsMap = new Map();
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result);
    });
  }
  const loginResultMap = loginStatusResults.value || {};
  const loginTestingMap = loginStatusTesting.value || {};

  let list = (plugins.value || []).map((plugin) => {
    // Find associated site info
    const primarySite = plugin.sites?.[0] || null;
    const siteName = primarySite?.site_name || primarySite?.name || '';
    const siteResult = resultsMap.get(siteName) || {};
    const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || null;
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

const setLoginTesting = (siteName, value) => {
  if (!siteName) return;
  loginStatusTesting.value = {
    ...loginStatusTesting.value,
    [siteName]: value
  };
};

const stopYouTubeOAuthPolling = () => {
  if (ytOAuthPollTimer !== null) {
    clearInterval(ytOAuthPollTimer);
    ytOAuthPollTimer = null;
  }
};

const upsertYouTubeOAuthStatus = (payload = {}) => {
  const current = loginStatusResults.value?.youtube || {};
  upsertLoginStatus('youtube', {
    ...current,
    oauth_status: payload.status || 'not_configured',
    oauth_account: payload.account || null,
    verification_url: payload.verification_url || null,
    user_code: payload.user_code || null,
    message: payload.error || current.message || '',
    checked_at: new Date().toISOString(),
  });
};

const pollYouTubeOAuthStatus = async () => {
  const { data, error } = await getYouTubeOAuthStatus();
  if (error || !data) {
    upsertYouTubeOAuthStatus({
      status: 'error',
      error: error?.message || 'OAuth 状态查询失败',
    });
    stopYouTubeOAuthPolling();
    saveResultsToCache();
    return;
  }

  upsertYouTubeOAuthStatus(data);
  if (data.status !== 'pending') {
    stopYouTubeOAuthPolling();
  }
  saveResultsToCache();
};

const startYouTubeOAuthPolling = () => {
  stopYouTubeOAuthPolling();
  ytOAuthPollTimer = setInterval(pollYouTubeOAuthStatus, 3000);
};

const showYouTubeOAuthPendingNotice = (payload) => {
  if (payload?.verification_url) {
    window.open(payload.verification_url, '_blank', 'noopener,noreferrer');
  }

  const lines = ['请在浏览器中完成 YouTube 授权。'];
  if (payload?.user_code) {
    lines.push(`验证码：${payload.user_code}`);
  }
  if (payload?.verification_url) {
    lines.push(`链接：${payload.verification_url}`);
  }
  alert(lines.join('\n'));
};

const handleStartYouTubeOAuth = async () => {
  ytOAuthActioning.value = true;
  try {
    const { data, error } = await setupYouTubeOAuth();
    if (error || !data) {
      upsertYouTubeOAuthStatus({
        status: 'error',
        error: error?.message || 'OAuth 启动失败',
      });
      saveResultsToCache();
      return;
    }

    upsertYouTubeOAuthStatus(data);
    saveResultsToCache();

    if (data.status === 'pending') {
      showYouTubeOAuthPendingNotice(data);
      startYouTubeOAuthPolling();
    }
  } finally {
    ytOAuthActioning.value = false;
  }
};

const handleRevokeYouTubeOAuth = async () => {
  ytOAuthActioning.value = true;
  stopYouTubeOAuthPolling();
  try {
    const { data, error } = await revokeYouTubeOAuth();
    if (error || !data?.revoked) {
      upsertYouTubeOAuthStatus({
        status: 'error',
        error: error?.message || '撤销授权失败',
      });
      saveResultsToCache();
      return;
    }

    upsertYouTubeOAuthStatus({
      status: 'not_configured',
      account: null,
      verification_url: null,
      user_code: null,
      error: null,
    });
    saveResultsToCache();
  } finally {
    ytOAuthActioning.value = false;
  }
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
  } catch (error) {
    Logger.error('Failed to load site config', error);
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

const setCookieUploading = (siteName, value) => {
  cookieUploading.value = {
    ...cookieUploading.value,
    [siteName]: value
  };
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

// Handlers for plugin-integrated site actions
const handleTestSingleBySite = async (siteName) => {
  if (!siteName) return;
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
};

const handleTestLoginBySite = async (siteName) => {
  if (!siteName) return;
  setLoginTesting(siteName, true);
  try {
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
  } finally {
    setLoginTesting(siteName, false);
    saveResultsToCache();
  }
};

const handleUploadCookiesBySite = (siteName) => {
  if (!siteName) return;
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

const openSiteEditorByPlugin = (plugin) => {
  const siteName = plugin.siteName;
  if (!siteName) return;

  // Find or create site info from catalog
  const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || {};
  editingSite.value = {
    slug: siteName,
    label: catalogInfo.label || plugin.display_name || siteName,
    enabled: catalogInfo.enabled !== false,
    test_url: catalogInfo.test_url || '',
    domains: catalogInfo.domains || [],
    iconUrl: catalogInfo.icon_url || '',
  };
  siteEditorError.value = '';
  siteEditorVisible.value = true;
};

onMounted(() => {
  fetchPlugins();
  loadSiteCatalog();
  loadResultsFromCache();
  fetchSupportedSites();
});

onUnmounted(() => {
  stopYouTubeOAuthPolling();
});
</script>

<style scoped>
.plugin-page {
  min-height: 100%;
}

.content-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 var(--app-page-gutter);
}

@media (min-width: 640px) {
  .content-container {
    padding: 0 var(--app-page-gutter-sm);
  }
}

@media (min-width: 1024px) {
  .content-container {
    padding: 0 var(--app-page-gutter-lg);
  }
}

.plugin-shell {
  padding-top: 0.5rem;
}

.plugin-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  padding: var(--app-toolbar-padding-block) 0;
  flex-wrap: wrap;
}

.plugin-empty-state {
  margin-top: 0.75rem;
}

.plugin-toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.plugin-toolbar-skeleton {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
  width: 100%;
}

.plugin-toolbar-skeleton__chip {
  height: 1.75rem;
  border-radius: calc(var(--radius-sm) - 1px);
}

.plugin-toolbar-skeleton__chip:last-child {
  margin-left: 0.25rem;
}

.plugin-toolbar-btn {
  gap: 4px;
  border-radius: calc(var(--radius-sm) - 1px);
}

.plugin-toolbar-btn--quiet {
  border-color: hsl(var(--border) / 0.6);
  background: hsl(var(--background));
  box-shadow: none;
}

.plugin-toolbar-btn--quiet:hover {
  background: hsl(var(--accent) / 0.6);
  color: hsl(var(--accent-foreground));
}

.plugin-toolbar-btn--primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}

.plugin-toolbar-btn--primary:hover {
  background: hsl(var(--primary) / 0.9);
}

.plugin-stats-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
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

.plugin-stat-skeleton {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.plugin-stat-skeleton__value {
  height: 0.9rem;
  border-radius: 999px;
}

.plugin-stat-skeleton__label {
  height: 0.7rem;
  border-radius: 999px;
  opacity: 0.85;
}

.plugin-timestamp {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground) / 0.4);
  margin-left: auto;
}

.plugin-timestamp--skeleton {
  width: 7.5rem;
  height: 0.85rem;
  border-radius: 999px;
  margin-left: 0.25rem;
}

.plugin-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: hsl(var(--secondary) / 0.3);
  border-radius: calc(var(--radius-sm) - 1px);
  color: hsl(var(--muted-foreground) / 0.5);
  margin-left: auto;
}

.plugin-search--skeleton {
  min-width: 8.75rem;
}

.plugin-search__icon-skeleton {
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 999px;
  flex-shrink: 0;
}

.plugin-search__input-skeleton {
  width: 6rem;
  height: 0.72rem;
  border-radius: 999px;
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

.plugin-search-refresh {
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
}

.plugin-search-refresh--skeleton {
  border-radius: calc(var(--radius-sm) - 1px);
}

.plugin-content {
  padding-top: 0.5rem;
}

.plugin-unified-panel {
  border: 1px solid hsl(var(--border) / 0.45);
  border-radius: 0.875rem;
  background: hsl(var(--card) / 0.45);
  overflow: hidden;
}

.plugin-unified-section {
  padding: 0.5rem 0;
}

.plugin-unified-section + .plugin-unified-section {
  border-top: 1px solid hsl(var(--border) / 0.35);
}

.plugin-unified-section__head {
  padding: 0.5rem 0.75rem 0.375rem;
  font-size: 0.6875rem;
  font-weight: 700;
  color: hsl(var(--muted-foreground) / 0.7);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.plugin-loading,
.plugin-empty {
  display: none;
}

.plugin-skeleton-wrap {
  display: block;
}

.skeleton-surface {
  position: relative;
  overflow: hidden;
  background: linear-gradient(
    180deg,
    hsl(var(--foreground) / 0.06),
    hsl(var(--foreground) / 0.03)
  );
  border: 1px solid hsl(var(--border) / 0.12);
}

.skeleton-surface::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    hsl(var(--foreground) / 0.05),
    transparent
  );
  animation: plugin-skeleton-shimmer 1.8s infinite;
}

@keyframes plugin-skeleton-shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.plugin-inline-loading,
.plugin-inline-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 7rem;
  gap: 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
}

/* Alert */
.plugin-alert {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.125rem;
  border-radius: 0.875rem;
  font-size: 0.8125rem;
  font-weight: 500;
  margin-bottom: 1rem;
  border-width: 1px;
}

.plugin-alert--error {
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
  border-color: hsl(var(--destructive) / 0.2);
}

/* Site Config Grid */
.site-config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0;
  padding: 0 0.75rem 0.5rem;
}

.site-config-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1rem 1.25rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 1rem;
  cursor: pointer;
  transition:
    all var(--duration-normal) var(--ease-default);
}

.site-config-item:hover {
  border-color: hsl(var(--primary) / 0.3);
  background: hsl(var(--secondary) / 0.2);
}

.site-config-icon {
  flex-shrink: 0;
  border: 1px solid hsl(var(--border) / 0.3);
}

.site-config-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.site-config-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  truncate: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.site-config-slug {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground) / 0.5);
  font-family: 'JetBrains Mono', monospace;
}

.site-config-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.site-config-status--enabled {
  background: hsl(var(--success));
  box-shadow: 0 0 6px hsl(var(--success) / 0.4);
}

.site-config-status--disabled {
  background: hsl(var(--muted-foreground) / 0.2);
}

/* Table */
.plugin-table-wrap {
  overflow-x: auto;
  padding: 0 0.5rem;
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
.col-site-access { min-width: 90px; }
.col-site-login { min-width: 80px; }
.col-latency { width: 70px; text-align: center; }
.col-domains { min-width: 140px; }
.col-actions { width: 120px; text-align: right; }

/* Cell styles */
.name-primary {
  font-weight: 600;
  color: hsl(var(--foreground));
}

/* Caps cell */
.caps-inline {
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 2px;
  white-space: nowrap;
}

.cap-tag {
  display: inline-block;
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 3px;
  white-space: nowrap;
  background: hsl(var(--secondary));
  color: hsl(var(--muted-foreground));
}

.cap-more {
  font-size: 10px;
  color: hsl(var(--muted-foreground) / 0.5);
  margin-left: 2px;
}

.cap-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.cap-tooltip {
  display: none;
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
  border: 1px solid hsl(var(--border));
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  white-space: pre-line;
  line-height: 1.5;
  z-index: 50;
  box-shadow: 0 4px 12px hsl(0 0% 0% / 0.15);
  min-width: 100px;
  max-width: 250px;
}

.cap-wrapper:hover .cap-tooltip {
  display: block;
}

.cap-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: hsl(var(--popover));
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
.status-error,
.status-warning {
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

.status-warning {
  color: hsl(var(--warning));
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
  transition: all var(--duration-fast) var(--ease-default);
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

  .plugin-toolbar-skeleton,
  .plugin-toolbar-right {
    justify-content: flex-end;
  }

  .plugin-stats-row {
    gap: 0.5rem;
  }

  .plugin-timestamp--skeleton,
  .plugin-search,
  .plugin-search--skeleton {
    margin-left: 0;
  }

  .col-endpoint,
  .col-caps {
    display: none;
  }
}
</style>

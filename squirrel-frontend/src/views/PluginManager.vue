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
              <p class="plugin-summary-card__label">运行中</p>
              <p class="plugin-summary-card__value text-success">{{ pluginSummary.running }}</p>
            </CardContent>
          </Card>
          <Card class="plugin-summary-card">
            <CardContent class="p-4">
              <p class="plugin-summary-card__label">异常或停用</p>
              <p class="plugin-summary-card__value text-warning">{{ pluginSummary.attention }}</p>
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
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground hidden lg:table-cell">能力与站点</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground hidden xl:table-cell">权限</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-muted-foreground">运行时</th>
                  <th class="text-right py-3 px-4 text-sm font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="plugin in displayPlugins"
                  :key="plugin.plugin_id"
                  class="plugin-table-shell__row border-b border-border"
                >
                  <td class="py-4 px-4">
                    <div class="space-y-2">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="font-medium">{{ plugin.display_name }}</span>
                        <span class="plugin-tag plugin-tag--muted">{{ plugin.plugin_id }}</span>
                      </div>
                      <div class="text-xs text-muted-foreground">
                        {{ plugin.description || '未提供插件描述' }}
                      </div>
                      <div class="flex flex-wrap gap-1 lg:hidden">
                        <span class="plugin-tag plugin-tag--muted">{{ plugin.capabilityCount }} 个能力</span>
                        <span class="plugin-tag plugin-tag--muted">{{ plugin.siteCount }} 个站点</span>
                        <span class="plugin-tag" :class="getPluginStatusClass(plugin)">
                          {{ getPluginStatusLabel(plugin) }}
                        </span>
                        <span class="plugin-tag" :class="getPluginHealthClass(plugin)">
                          {{ getPluginHealthLabel(plugin) }}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td class="py-4 px-4 text-muted-foreground text-sm">
                    <div class="font-medium text-foreground">{{ plugin.version || '—' }}</div>
                    <div class="mt-1 text-xs text-muted-foreground">
                      {{ plugin.active_runtime?.endpoint || '运行时未启动' }}
                    </div>
                  </td>
                  <td class="py-4 px-4 hidden lg:table-cell">
                    <div class="space-y-2">
                      <div class="flex flex-wrap gap-1">
                        <span class="plugin-tag plugin-tag--muted">{{ plugin.capabilityCount }} 个能力</span>
                        <span class="plugin-tag plugin-tag--muted">{{ plugin.siteCount }} 个站点</span>
                      </div>
                      <div class="flex flex-wrap gap-1">
                        <span
                          v-for="capability in plugin.capabilities.slice(0, 2)"
                          :key="`${plugin.plugin_id}-${capability.name}`"
                          class="plugin-tag plugin-tag--info"
                        >
                          {{ capability.name }}
                        </span>
                        <span
                          v-if="plugin.capabilities.length > 2"
                          class="plugin-tag plugin-tag--muted"
                        >
                          +{{ plugin.capabilities.length - 2 }}
                        </span>
                      </div>
                      <div class="text-xs text-muted-foreground">
                        {{ formatSiteNames(plugin.sites) }}
                      </div>
                    </div>
                  </td>
                  <td class="py-4 px-4 hidden xl:table-cell">
                    <div class="space-y-2">
                      <div class="flex flex-wrap gap-1">
                        <span class="plugin-tag plugin-tag--muted">
                          {{ plugin.permissionCount }} 项权限
                        </span>
                      </div>
                      <div class="flex flex-wrap gap-1">
                        <span
                          v-for="permission in plugin.permissions.slice(0, 2)"
                          :key="`${plugin.plugin_id}-${permission.name}`"
                          class="plugin-tag plugin-tag--warning"
                          :title="permission.description || permission.name"
                        >
                          {{ permission.name }}
                        </span>
                        <span
                          v-if="plugin.permissions.length > 2"
                          class="plugin-tag plugin-tag--muted"
                        >
                          +{{ plugin.permissions.length - 2 }}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex flex-col items-center gap-2 text-center">
                      <span class="plugin-tag" :class="getPluginStatusClass(plugin)">
                        {{ getPluginStatusLabel(plugin) }}
                      </span>
                      <span class="plugin-tag" :class="getPluginHealthClass(plugin)">
                        {{ getPluginHealthLabel(plugin) }}
                      </span>
                      <div class="text-xs text-muted-foreground max-w-[200px]">
                        {{ plugin.health?.message || plugin.active_runtime?.last_error || plugin.runtimeStateLabel }}
                      </div>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex items-center justify-end gap-2">
                      <Button
                        v-if="!plugin.enabled"
                        :disabled="actioning === plugin.plugin_id"
                        @click="handleEnable(plugin)"
                        size="xs"
                        variant="outline"
                        class="plugin-inline-action"
                      >
                        启用
                      </Button>
                      <Button
                        v-if="plugin.enabled"
                        :disabled="actioning === plugin.plugin_id"
                        @click="handleDisable(plugin)"
                        size="xs"
                        variant="ghost"
                        class="plugin-inline-action"
                      >
                        禁用
                      </Button>
                      <Button
                        :disabled="actioning === plugin.plugin_id"
                        @click="handleUninstall(plugin)"
                        size="xs"
                        variant="destructive"
                        class="plugin-inline-action plugin-inline-action--danger"
                      >
                        卸载
                      </Button>
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
                      <Button
                        @click="handleTestSingle(site)"
                        :disabled="site.testing || testingAll"
                        size="xs"
                        variant="outline"
                        class="plugin-inline-action"
                      >
                        {{ site.testing ? '测试中...' : '连通性' }}
                      </Button>
                      <Button
                        v-if="site.supports_login_status"
                        @click="handleTestLogin(site)"
                        :disabled="site.loginTesting || testingAll"
                        size="xs"
                        variant="ghost"
                        class="plugin-inline-action"
                      >
                        {{ site.loginTesting ? '检测中...' : '登录检测' }}
                      </Button>
                      <Button
                        @click="handleUploadCookies(site)"
                        :disabled="site.cookieUploading || testingAll"
                        size="xs"
                        variant="outline"
                        class="plugin-inline-action"
                      >
                        {{ site.cookieUploading ? '上传中...' : '上传Cookie' }}
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
  CheckCircleIcon
} from '@heroicons/vue/24/outline';
import PageHeader from '@/components/layout/PageHeader.vue'
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import { Button } from '@/components/ui/button'
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

const displayPlugins = computed(() => (
  (plugins.value || []).map((plugin) => {
    const capabilities = Array.isArray(plugin.capabilities) ? plugin.capabilities : [];
    const sites = Array.isArray(plugin.sites) ? plugin.sites : [];
    const permissions = Array.isArray(plugin.permissions) ? plugin.permissions : [];
    const activeRuntime = plugin.active_runtime || null;
    const health = plugin.health || activeRuntime?.health || null;

    return {
      ...plugin,
      capabilities,
      sites,
      permissions,
      active_runtime: activeRuntime,
      health,
      capabilityCount: capabilities.length,
      siteCount: sites.length,
      permissionCount: permissions.length,
      runtimeStateLabel: runtimeStateLabels[activeRuntime?.state] || '运行时未启动',
    };
  })
));

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

const getPluginStatusLabel = (plugin) => pluginStatusLabels[plugin.status] || plugin.status || '未知状态';

const getPluginStatusClass = (plugin) => {
  if (['running'].includes(plugin.status)) return 'plugin-tag--success';
  if (['starting', 'installed', 'validated', 'uploaded'].includes(plugin.status)) return 'plugin-tag--info';
  if (['degraded'].includes(plugin.status)) return 'plugin-tag--warning';
  if (['failed'].includes(plugin.status)) return 'plugin-tag--danger';
  return 'plugin-tag--muted';
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
  const names = (sites || []).map(site => site.site_name).filter(Boolean);
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

.plugin-summary-card,
.plugin-loading-shell,
.plugin-table-shell,
.plugin-last-tested {
  border: 1px solid hsl(var(--border) / 0.76);
  background: linear-gradient(180deg, hsl(var(--card)), hsl(var(--card) / 0.94));
  box-shadow: 0 12px 28px hsl(var(--foreground) / 0.035);
}

.plugin-summary-card__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: hsl(var(--muted-foreground));
}

.plugin-hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.plugin-tab-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem;
  border-radius: 0.625rem;
  border: 1px solid hsl(var(--border) / 0.8);
  background: hsl(var(--background));
}

.plugin-tab-switch__button {
  padding: 0.45rem 0.75rem;
  border-radius: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
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
  box-shadow: var(--shadow-sm);
}

.plugin-primary-action,
.plugin-inline-action {
  transition: opacity 160ms ease;
}

.plugin-pill-icon {
  box-shadow: none;
}

.plugin-upload-button {
  max-width: 16rem;
}

.plugin-primary-action {
  box-shadow: none;
}

.plugin-inline-action {
  box-shadow: none;
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
  margin-top: 0.65rem;
  font-size: 1.65rem;
  line-height: 1;
  font-weight: 600;
}

.plugin-loading-shell,
.plugin-table-shell {
  border-radius: 0.875rem;
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
  padding: 0.55rem 0.8rem;
  border-radius: 0.625rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.plugin-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.22rem 0.55rem;
  border-radius: 0.5rem;
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

</style>

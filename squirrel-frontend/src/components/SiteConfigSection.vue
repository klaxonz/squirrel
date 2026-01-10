<template>
  <div class="settings-section mb-8">
    <h2 class="text-lg font-semibold mb-4 text-text-secondary">站点配置</h2>
    <p class="text-sm text-text-muted mb-3">管理各站点的域名、代理与抓取参数，用于订阅与视频来源识别。</p>

    <div v-if="siteLoading" class="py-6 text-sm text-text-muted">
      正在加载站点配置...
    </div>

    <div v-else>
      <div v-if="siteError" class="mb-3 text-sm text-color-error">
        {{ siteError.message || siteError }}
      </div>

      <div v-if="siteList.length === 0" class="py-6 text-sm text-text-muted">
        暂无站点配置。
      </div>

      <!-- 列表外框：与页面背景接近的深灰，弱化存在感 -->
      <div v-else class="border border-border-secondary rounded-xl overflow-hidden bg-bg-primary">
        <div class="grid grid-cols-6 px-4 py-2 text-xs text-text-tertiary bg-bg-secondary">
          <div class="col-span-2">站点</div>
          <div class="col-span-2">域名</div>
          <div class="col-span-1 text-center">状态</div>
          <div class="col-span-1 text-right">操作</div>
        </div>
        <div
          v-for="site in siteList"
          :key="site.slug"
          class="grid grid-cols-6 px-4 py-3 text-sm border-t border-border-primary hover:bg-bg-hover transition-colors items-center"
        >
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ site.label }}</span>
              <span class="text-xs text-text-tertiary">({{ site.slug }})</span>
            </div>
          </div>
          <div class="col-span-2 text-xs text-text-muted truncate">
            <span v-if="site.domains && site.domains.length">{{ site.domains.join(', ') }}</span>
            <span v-else class="italic">未配置</span>
          </div>
          <div class="col-span-1 flex justify-center">
            <span
              class="px-2 py-0.5 rounded-full text-xs font-medium"
              :class="site.enabled ? 'bg-color-success/10 text-color-success' : 'bg-bg-tertiary text-text-secondary'"
            >
              {{ site.enabled ? '已启用' : '已禁用' }}
            </span>
          </div>
          <div class="col-span-1 flex justify-end">
            <button
              class="px-3 py-1.5 bg-bg-elevated hover:bg-bg-hover rounded-full text-xs font-medium transition-colors"
              @click="openSiteEditor(site)"
            >
              配置
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 站点配置编辑弹窗 -->
    <div
      v-if="siteEditorVisible"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
    >
      <div class="bg-bg-secondary rounded-2xl border border-border-secondary w-full max-w-3xl shadow-xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-secondary">
          <div>
            <h3 class="text-lg font-semibold">编辑站点配置</h3>
            <p class="text-xs text-text-muted mt-1">站点标识：{{ siteEditorForm.slug }}</p>
          </div>
          <button
            class="text-text-muted hover:text-text-primary transition-colors"
            @click="closeSiteEditor"
          >
            ✕
          </button>
        </div>

        <div class="site-editor-scroll px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto pr-2 text-sm">
          <LabeledTextInput
            label="显示名称"
            v-model="siteEditorForm.label"
            placeholder="展示给用户的名称"
          />

          <div class="grid md:grid-cols-2 gap-4">
            <LabeledTextarea
              label="域名列表"
              v-model="siteEditorForm.domainsText"
              :rows="4"
              placeholder="每行一个域名，例如：www.youtube.com"
            />
            <LabeledTextarea
              label="别名（可选）"
              v-model="siteEditorForm.aliasesText"
              :rows="4"
              placeholder="每行一个别名，例如：yt、油管"
            />
          </div>

          <div class="flex items-center gap-3 text-sm text-text-secondary">
            <LabeledCheckbox
              label="启用该站点（用于筛选/数据爬取）"
              v-model="siteEditorForm.enabled"
            />
          </div>

          <LabeledTextInput
            label="测试 URL"
            v-model="siteEditorForm.testUrl"
            placeholder="用于连通性检测的 URL"
          />

          <LabeledTextarea
            label="HTTP 请求头（每行 key: value）"
            v-model="siteEditorForm.httpHeadersText"
            :rows="3"
            placeholder="User-Agent: Mozilla/5.0"
          />

          <div class="grid md:grid-cols-2 gap-4">
            <LabeledNumberInput
              label="最小请求间隔（秒）"
              v-model="siteEditorForm.rateLimitMin"
              :step="0.1"
            />
            <LabeledNumberInput
              label="最大请求间隔（秒）"
              v-model="siteEditorForm.rateLimitMax"
              :step="0.1"
            />
          </div>

          <div>
            <h4 class="text-xs text-text-secondary mb-2">代理参数</h4>
            <div class="grid md:grid-cols-2 gap-4 text-sm text-text-secondary">
              <LabeledNumberInput
                label="连接超时 (秒)"
                v-model="siteEditorForm.proxyConnectTimeout"
                :step="0.1"
              />
              <LabeledNumberInput
                label="读取超时 (秒)"
                v-model="siteEditorForm.proxyReadTimeout"
                :step="0.1"
              />
              <LabeledNumberInput
                label="写入超时 (秒)"
                v-model="siteEditorForm.proxyWriteTimeout"
                :step="0.1"
              />
              <LabeledNumberInput
                label="连接池超时 (秒)"
                v-model="siteEditorForm.proxyPoolTimeout"
                :step="0.1"
              />
              <LabeledNumberInput
                label="Keepalive 过期 (秒)"
                v-model="siteEditorForm.proxyKeepaliveExpiry"
                :step="0.1"
              />
              <LabeledNumberInput
                label="最大连接数"
                v-model="siteEditorForm.proxyMaxConnections"
                :step="1"
              />
              <LabeledNumberInput
                label="最大 Keepalive 连接数"
                v-model="siteEditorForm.proxyMaxKeepaliveConnections"
                :step="1"
              />
              <LabeledNumberInput
                label="分块大小 (字节)"
                v-model="siteEditorForm.proxyChunkSize"
                :step="1"
              />
              <LabeledNumberInput
                label="最大重试次数"
                v-model="siteEditorForm.proxyMaxRetries"
                :step="1"
              />
            </div>
            <div class="flex flex-wrap gap-4 mt-3 text-xs text-text-secondary">
              <LabeledCheckbox
                label="启用 HTTP/2"
                v-model="siteEditorForm.proxyEnableHttp2"
              />
              <LabeledCheckbox
                label="允许重定向"
                v-model="siteEditorForm.proxyFollowRedirects"
              />
            </div>
          </div>

          <div>
            <h4 class="text-xs text-text-secondary mb-2">登录检测</h4>
            <div class="grid md:grid-cols-2 gap-4">
              <LabeledTextInput
                label="检测 URL"
                v-model="siteEditorForm.loginCheckUrl"
                placeholder="检测 URL"
              />
              <LabeledNumberInput
                label="超时时间 (秒)"
                v-model="siteEditorForm.loginTimeout"
                :step="0.1"
              />
            </div>
            <LabeledTextarea
              label="登录检测请求头"
              v-model="siteEditorForm.loginHeadersText"
              :rows="3"
              placeholder="登录检测请求头，每行 key: value"
              class="mt-3"
            />
          </div>

          <div class="flex flex-wrap gap-4 text-xs text-text-secondary">
            <LabeledCheckbox
              label="默认标记为 NSFW"
              v-model="siteEditorForm.metadataNsfw"
            />
            <LabeledCheckbox
              label="需要 Cookies 才可抓取"
              v-model="siteEditorForm.metadataRequiresCookies"
            />
            <LabeledCheckbox
              label="需要登录状态"
              v-model="siteEditorForm.metadataRequiresLogin"
            />
            <LabeledCheckbox
              label="启用播放器链接缓存"
              v-model="siteEditorForm.metadataPlayerUrlCache"
            />
            <LabeledCheckbox
              label="解析时下载封面到本地"
              v-model="siteEditorForm.metadataOfflineThumbnailsDownload"
            />
            <LabeledCheckbox
              label="优先使用本地封面显示"
              v-model="siteEditorForm.metadataOfflineThumbnailsDisplay"
            />
          </div>

          <div
            v-if="siteEditorError"
            class="text-sm text-color-error bg-color-error/10 border border-color-error/30 rounded-lg px-4 py-2"
          >
            {{ siteEditorError }}
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-secondary">
          <button
            @click="closeSiteEditor"
            class="px-5 py-2 rounded-full bg-bg-tertiary hover:bg-bg-hover text-sm transition-colors"
          >
            取消
          </button>
          <button
            @click="saveSiteEditor"
            :disabled="siteEditorSaving"
            class="px-5 py-2 rounded-full bg-color-error hover:bg-color-error-hover text-sm font-medium transition-colors disabled:opacity-50"
          >
            {{ siteEditorSaving ? '保存中...' : '保存配置' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useSiteCatalog } from '../composables/useSites';
import LabeledNumberInput from './LabeledNumberInput.vue';
import LabeledTextarea from './LabeledTextarea.vue';
import LabeledTextInput from './LabeledTextInput.vue';
import LabeledCheckbox from './LabeledCheckbox.vue';

const { catalog: siteCatalog, loading: siteLoading, error: siteError, loadCatalog, saveCatalog } = useSiteCatalog();

const siteEditorVisible = ref(false);
const siteEditorSaving = ref(false);
const siteEditorError = ref('');
const siteEditorForm = ref({
  slug: '',
  siteName: '',
  label: '',
  domainsText: '',
  aliasesText: '',
  enabled: true,
  testUrl: '',
  httpHeadersText: '',
  rateLimitMin: '',
  rateLimitMax: '',
  proxyConnectTimeout: '',
  proxyReadTimeout: '',
  proxyWriteTimeout: '',
  proxyPoolTimeout: '',
  proxyKeepaliveExpiry: '',
  proxyMaxConnections: '',
  proxyMaxKeepaliveConnections: '',
  proxyChunkSize: '',
  proxyMaxRetries: '',
  proxyEnableHttp2: true,
  proxyFollowRedirects: true,
  loginCheckUrl: '',
  loginHeadersText: '',
  loginTimeout: '',
  metadataNsfw: false,
  metadataRequiresCookies: false,
  metadataRequiresLogin: false,
  metadataPlayerUrlCache: false,
  metadataOfflineThumbnailsDownload: false,
  metadataOfflineThumbnailsDisplay: false,
});

const siteList = computed(() => {
  const catalog = siteCatalog.value || {};
  return Object.entries(catalog).map(([slug, info]) => ({
    slug,
    label: info?.label || slug,
    enabled: info?.enabled !== false,
    test_url: info?.test_url || '',
    domains: info?.domains || [],
  }));
});

onMounted(async () => {
  await loadCatalog();
});

const parseListInput = (text = '') => {
  return text
    .split(/[\n,]/)
    .map(item => item.trim())
    .filter(Boolean);
};

const headersToText = (headers = {}) => {
  return Object.entries(headers || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n');
};

const parseHeadersText = (text = '') => {
  const result = {};
  text.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const [key, ...rest] = trimmed.split(':');
    if (!key) return;
    result[key.trim()] = rest.join(':').trim();
  });
  return result;
};

const toNumberOrUndefined = (value) => {
  if (value === '' || value === null || value === undefined) {
    return undefined;
  }
  const num = Number(value);
  return Number.isNaN(num) ? undefined : num;
};

const openSiteEditor = (site) => {
  const slug = site.slug;
  const catalogInfo = siteCatalog.value[slug] || {};
  const rateLimit = catalogInfo?.rate_limit || {};
  const proxy = catalogInfo?.proxy || {};
  const loginConfig = catalogInfo?.login || {};
  const metadata = catalogInfo?.metadata || {};

  siteEditorForm.value = {
    slug,
    siteName: site.label,
    label: catalogInfo?.label || site.label,
    domainsText: (catalogInfo?.domains || site.domains || []).join('\n'),
    aliasesText: (catalogInfo?.aliases || []).join('\n'),
    enabled: catalogInfo?.enabled !== false,
    testUrl: catalogInfo?.test_url || '',
    httpHeadersText: headersToText(catalogInfo?.http?.headers || {}),
    rateLimitMin: rateLimit?.min_interval ?? '',
    rateLimitMax: rateLimit?.max_interval ?? '',
    proxyConnectTimeout: proxy?.connect_timeout ?? '',
    proxyReadTimeout: proxy?.read_timeout ?? '',
    proxyWriteTimeout: proxy?.write_timeout ?? '',
    proxyPoolTimeout: proxy?.pool_timeout ?? '',
    proxyKeepaliveExpiry: proxy?.keepalive_expiry ?? '',
    proxyMaxConnections: proxy?.max_connections ?? '',
    proxyMaxKeepaliveConnections: proxy?.max_keepalive_connections ?? '',
    proxyChunkSize: proxy?.chunk_size ?? '',
    proxyMaxRetries: proxy?.max_retries ?? '',
    proxyEnableHttp2: proxy?.enable_http2 !== false,
    proxyFollowRedirects: proxy?.follow_redirects !== false,
    loginCheckUrl: loginConfig?.check_url || '',
    loginHeadersText: headersToText(loginConfig?.headers || {}),
    loginTimeout: loginConfig?.timeout ?? '',
    metadataNsfw: !!metadata?.nsfw,
    metadataRequiresCookies: !!metadata?.requires_cookies,
    metadataRequiresLogin: !!metadata?.requires_login,
    metadataPlayerUrlCache: !!metadata?.player_url_cache,
    metadataOfflineThumbnailsDownload: !!metadata?.offline_thumbnails_download,
    metadataOfflineThumbnailsDisplay: !!metadata?.offline_thumbnails_display,
  };
  siteEditorError.value = '';
  siteEditorVisible.value = true;
};

const closeSiteEditor = () => {
  siteEditorVisible.value = false;
  siteEditorError.value = '';
};

const saveSiteEditor = async () => {
  siteEditorError.value = '';
  const { slug, siteName } = siteEditorForm.value;
  if (!slug) {
    siteEditorError.value = '站点标识不可为空';
    return;
  }
  const domains = parseListInput(siteEditorForm.value.domainsText);
  if (!domains.length) {
    siteEditorError.value = '请至少填写一个域名';
    return;
  }
  const aliases = parseListInput(siteEditorForm.value.aliasesText);
  const label = siteEditorForm.value.label?.trim() || siteName || slug;

  const httpHeaders = parseHeadersText(siteEditorForm.value.httpHeadersText);
  const loginHeaders = parseHeadersText(siteEditorForm.value.loginHeadersText);
  const rateLimitMin = toNumberOrUndefined(siteEditorForm.value.rateLimitMin);
  const rateLimitMax = toNumberOrUndefined(siteEditorForm.value.rateLimitMax);
  const proxyPayload = {};
  const proxyFields = [
    ['connect_timeout', siteEditorForm.value.proxyConnectTimeout],
    ['read_timeout', siteEditorForm.value.proxyReadTimeout],
    ['write_timeout', siteEditorForm.value.proxyWriteTimeout],
    ['pool_timeout', siteEditorForm.value.proxyPoolTimeout],
    ['keepalive_expiry', siteEditorForm.value.proxyKeepaliveExpiry],
    ['max_connections', siteEditorForm.value.proxyMaxConnections],
    ['max_keepalive_connections', siteEditorForm.value.proxyMaxKeepaliveConnections],
    ['chunk_size', siteEditorForm.value.proxyChunkSize],
    ['max_retries', siteEditorForm.value.proxyMaxRetries],
  ];
  proxyFields.forEach(([key, value]) => {
    const num = toNumberOrUndefined(value);
    if (num !== undefined) {
      proxyPayload[key] = num;
    }
  });
  proxyPayload.enable_http2 = !!siteEditorForm.value.proxyEnableHttp2;
  proxyPayload.follow_redirects = !!siteEditorForm.value.proxyFollowRedirects;

  const rateLimitPayload = {};
  if (rateLimitMin !== undefined) rateLimitPayload.min_interval = rateLimitMin;
  if (rateLimitMax !== undefined) rateLimitPayload.max_interval = rateLimitMax;

  const loginPayload = {};
  if (siteEditorForm.value.loginCheckUrl?.trim()) {
    loginPayload.check_url = siteEditorForm.value.loginCheckUrl.trim();
  }
  if (Object.keys(loginHeaders).length) {
    loginPayload.headers = loginHeaders;
  }
  const loginTimeout = toNumberOrUndefined(siteEditorForm.value.loginTimeout);
  if (loginTimeout !== undefined) {
    loginPayload.timeout = loginTimeout;
  }

  const metadataPayload = {
    nsfw: !!siteEditorForm.value.metadataNsfw,
    requires_cookies: !!siteEditorForm.value.metadataRequiresCookies,
    requires_login: !!siteEditorForm.value.metadataRequiresLogin,
    player_url_cache: !!siteEditorForm.value.metadataPlayerUrlCache,
    offline_thumbnails_download: !!siteEditorForm.value.metadataOfflineThumbnailsDownload,
    offline_thumbnails_display: !!siteEditorForm.value.metadataOfflineThumbnailsDisplay,
  };

  const sitePayload = {
    label,
    domains,
    aliases,
    enabled: !!siteEditorForm.value.enabled,
  };
  const testUrl = siteEditorForm.value.testUrl?.trim();
  if (testUrl) {
    sitePayload.test_url = testUrl;
  }
  if (Object.keys(httpHeaders).length) {
    sitePayload.http = { headers: httpHeaders };
  }
  if (Object.keys(rateLimitPayload).length) {
    sitePayload.rate_limit = rateLimitPayload;
  }
  if (Object.keys(proxyPayload).some(key => proxyPayload[key] !== undefined && proxyPayload[key] !== '')) {
    sitePayload.proxy = proxyPayload;
  }
  if (Object.keys(loginPayload).length) {
    sitePayload.login = loginPayload;
  }
  sitePayload.metadata = metadataPayload;

  const updatedCatalog = { ...siteCatalog.value };
  updatedCatalog[slug] = sitePayload;

  siteEditorSaving.value = true;
  try {
    await saveCatalog(updatedCatalog);
    siteEditorVisible.value = false;
  } catch (error) {
    console.error('保存站点配置失败:', error);
    siteEditorError.value = error?.message || '保存站点配置失败';
  } finally {
    siteEditorSaving.value = false;
  }
};
</script>

<style scoped>
.site-editor-scroll {
  /* Firefox */
  scrollbar-width: thin;
  scrollbar-color: var(--bg-tertiary) transparent;
}

.site-editor-scroll::-webkit-scrollbar {
  width: 6px;
}

.site-editor-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.site-editor-scroll::-webkit-scrollbar-thumb {
  background-color: var(--bg-tertiary);
  border-radius: 9999px;
}

.site-editor-scroll::-webkit-scrollbar-thumb:hover {
  background-color: var(--bg-hover);
}

/* 在站点配置弹窗内隐藏原生 number 输入的加减箭头，保持纯深色输入框样式 */
.site-editor-scroll input[type='number'] {
  -moz-appearance: textfield; /* Firefox */
}

.site-editor-scroll input[type='number']::-webkit-outer-spin-button,
.site-editor-scroll input[type='number']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>

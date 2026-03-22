<template>
  <div
    v-if="visible"
    class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
  >
    <div class="bg-card rounded-2xl border border-border w-full max-w-3xl shadow-xl">
      <div class="flex items-center justify-between px-6 py-4 border-b border-border">
        <div>
          <h3 class="text-lg font-semibold">编辑站点配置</h3>
          <p class="text-xs text-muted-foreground mt-1">站点标识：{{ siteEditorForm.slug }}</p>
        </div>
        <button
          class="text-muted-foreground hover:text-foreground transition-colors"
          @click="$emit('close')"
        >
          ✕
        </button>
      </div>

      <div class="site-editor-scroll px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto pr-2 text-sm">
        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">显示名称</Label>
          <Input v-model="siteEditorForm.label" placeholder="展示给用户的名称" />
        </div>

        <div class="grid md:grid-cols-2 gap-4">
          <div class="space-y-1">
            <Label class="text-xs text-muted-foreground">域名列表</Label>
            <Textarea v-model="siteEditorForm.domainsText" :rows="4" placeholder="每行一个域名，例如：www.youtube.com" />
          </div>
          <div class="space-y-1">
            <Label class="text-xs text-muted-foreground">别名（可选）</Label>
            <Textarea v-model="siteEditorForm.aliasesText" :rows="4" placeholder="每行一个别名，例如：yt、油管" />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <Checkbox :checked="!!siteEditorForm.enabled" @update:checked="(value) => siteEditorForm.enabled = !!value" />
          <Label class="text-sm font-normal text-muted-foreground">启用该站点（控制订阅与视频更新）</Label>
        </div>

        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">测试 URL</Label>
          <Input v-model="siteEditorForm.testUrl" placeholder="用于连通性检测的 URL" />
        </div>

        <div class="space-y-1">
          <Label class="text-xs text-muted-foreground">HTTP 请求头（每行 key: value）</Label>
          <Textarea v-model="siteEditorForm.httpHeadersText" :rows="3" placeholder="User-Agent: Mozilla/5.0" />
        </div>

        <div class="flex items-center gap-2">
          <Checkbox :checked="!!siteEditorForm.rateLimitEnabled" @update:checked="(value) => siteEditorForm.rateLimitEnabled = !!value" />
          <Label class="text-xs font-normal text-muted-foreground">启用站点限流</Label>
        </div>

        <div class="grid md:grid-cols-2 gap-4" :class="{ 'opacity-60': !siteEditorForm.rateLimitEnabled }">
          <div class="space-y-1">
            <Label class="text-xs text-muted-foreground">最小请求间隔（秒）</Label>
            <Input v-model="siteEditorForm.rateLimitMin" type="number" :step="0.1" :disabled="!siteEditorForm.rateLimitEnabled" />
          </div>
          <div class="space-y-1">
            <Label class="text-xs text-muted-foreground">最大请求间隔（秒）</Label>
            <Input v-model="siteEditorForm.rateLimitMax" type="number" :step="0.1" :disabled="!siteEditorForm.rateLimitEnabled" />
          </div>
        </div>

        <div>
          <h4 class="text-xs text-muted-foreground mb-2">代理参数</h4>
          <div class="grid md:grid-cols-2 gap-4 text-sm text-muted-foreground">
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">连接超时 (秒)</Label>
              <Input v-model="siteEditorForm.proxyConnectTimeout" type="number" :step="0.1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">读取超时 (秒)</Label>
              <Input v-model="siteEditorForm.proxyReadTimeout" type="number" :step="0.1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">写入超时 (秒)</Label>
              <Input v-model="siteEditorForm.proxyWriteTimeout" type="number" :step="0.1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">连接池超时 (秒)</Label>
              <Input v-model="siteEditorForm.proxyPoolTimeout" type="number" :step="0.1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">Keepalive 过期 (秒)</Label>
              <Input v-model="siteEditorForm.proxyKeepaliveExpiry" type="number" :step="0.1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">最大连接数</Label>
              <Input v-model="siteEditorForm.proxyMaxConnections" type="number" :step="1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">最大 Keepalive 连接数</Label>
              <Input v-model="siteEditorForm.proxyMaxKeepaliveConnections" type="number" :step="1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">分块大小 (字节)</Label>
              <Input v-model="siteEditorForm.proxyChunkSize" type="number" :step="1" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">最大重试次数</Label>
              <Input v-model="siteEditorForm.proxyMaxRetries" type="number" :step="1" />
            </div>
          </div>
          <div class="flex flex-wrap gap-4 mt-3 text-xs text-muted-foreground">
            <div class="flex items-center gap-2">
              <Checkbox :checked="!!siteEditorForm.proxyEnableHttp2" @update:checked="(value) => siteEditorForm.proxyEnableHttp2 = !!value" />
              <Label class="text-xs font-normal text-muted-foreground">启用 HTTP/2</Label>
            </div>
            <div class="flex items-center gap-2">
              <Checkbox :checked="!!siteEditorForm.proxyFollowRedirects" @update:checked="(value) => siteEditorForm.proxyFollowRedirects = !!value" />
              <Label class="text-xs font-normal text-muted-foreground">允许重定向</Label>
            </div>
          </div>
        </div>

        <div>
          <h4 class="text-xs text-muted-foreground mb-2">登录检测</h4>
          <div class="grid md:grid-cols-2 gap-4">
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">检测 URL</Label>
              <Input v-model="siteEditorForm.loginCheckUrl" placeholder="检测 URL" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs text-muted-foreground">超时时间 (秒)</Label>
              <Input v-model="siteEditorForm.loginTimeout" type="number" :step="0.1" />
            </div>
          </div>
          <div class="mt-3 space-y-1">
            <Label class="text-xs text-muted-foreground">登录检测请求头</Label>
            <Textarea v-model="siteEditorForm.loginHeadersText" :rows="3" placeholder="登录检测请求头，每行 key: value" />
          </div>
        </div>

        <div class="flex flex-wrap gap-4 text-xs text-muted-foreground">
          <div class="flex items-center gap-2">
            <Checkbox :checked="!!siteEditorForm.metadataNsfw" @update:checked="(value) => siteEditorForm.metadataNsfw = !!value" />
            <Label class="text-xs font-normal text-muted-foreground">默认标记为 NSFW</Label>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox :checked="!!siteEditorForm.metadataRequiresCookies" @update:checked="(value) => siteEditorForm.metadataRequiresCookies = !!value" />
            <Label class="text-xs font-normal text-muted-foreground">需要 Cookies 才可抓取</Label>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox :checked="!!siteEditorForm.metadataRequiresLogin" @update:checked="(value) => siteEditorForm.metadataRequiresLogin = !!value" />
            <Label class="text-xs font-normal text-muted-foreground">需要登录状态</Label>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox :checked="!!siteEditorForm.metadataPlayerUrlCache" @update:checked="(value) => siteEditorForm.metadataPlayerUrlCache = !!value" />
            <Label class="text-xs font-normal text-muted-foreground">启用播放器链接缓存</Label>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox :checked="!!siteEditorForm.metadataOfflineThumbnailsDownload" @update:checked="(value) => siteEditorForm.metadataOfflineThumbnailsDownload = !!value" />
            <Label class="text-xs font-normal text-muted-foreground">解析时下载封面到本地</Label>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox :checked="!!siteEditorForm.metadataOfflineThumbnailsDisplay" @update:checked="(value) => siteEditorForm.metadataOfflineThumbnailsDisplay = !!value" />
            <Label class="text-xs font-normal text-muted-foreground">优先使用本地封面显示</Label>
          </div>
        </div>

        <div
          v-if="resolvedError"
          class="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-lg px-4 py-2"
        >
          {{ resolvedError }}
        </div>
      </div>

      <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border">
        <Button variant="secondary" class="rounded-full" @click="$emit('close')">取消</Button>
        <Button variant="destructive" class="rounded-full" :disabled="saving" @click="handleSave">
          <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
          {{ saving ? '保存中...' : '保存配置' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

import { Loader2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  site: {
    type: Object,
    default: null,
  },
  catalog: {
    type: Object,
    default: () => ({}),
  },
  saving: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['close', 'save']);

const createEmptyForm = () => ({
  slug: '',
  siteName: '',
  label: '',
  domainsText: '',
  aliasesText: '',
  enabled: true,
  testUrl: '',
  httpHeadersText: '',
  rateLimitEnabled: true,
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

const siteEditorForm = ref(createEmptyForm());
const localError = ref('');

const headersToText = (headers = {}) => {
  return Object.entries(headers || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n');
};

const parseListInput = (text = '') => {
  return text
    .split(/[\n,]/)
    .map(item => item.trim())
    .filter(Boolean);
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

const buildFormFromSite = (site, catalog) => {
  const siteName = site?.site_name || site?.name || site?.label || site?.slug || '';
  const slug = site?.slug || String(siteName || '').toLowerCase();
  const catalogInfo = catalog?.[slug] || {};
  const rateLimit = catalogInfo?.rate_limit || {};
  const proxy = catalogInfo?.proxy || {};
  const loginConfig = catalogInfo?.login || {};
  const metadata = catalogInfo?.metadata || {};

  return {
    slug,
    siteName,
    label: catalogInfo?.label || site?.label || siteName || slug,
    domainsText: (catalogInfo?.domains?.length ? catalogInfo.domains : (site?.domains || [])).join('\n'),
    aliasesText: (catalogInfo?.aliases || []).join('\n'),
    enabled: catalogInfo?.enabled !== false,
    testUrl: catalogInfo?.test_url || site?.test_url || '',
    httpHeadersText: headersToText(catalogInfo?.http?.headers || {}),
    rateLimitEnabled: rateLimit?.enabled !== false,
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
};

const resolvedError = computed(() => {
  return localError.value || props.errorMessage;
});

const hydrateForm = () => {
  if (!props.site) {
    siteEditorForm.value = createEmptyForm();
    localError.value = '';
    return;
  }
  siteEditorForm.value = buildFormFromSite(props.site, props.catalog);
  localError.value = '';
};

const handleSave = () => {
  localError.value = '';
  const { slug, siteName } = siteEditorForm.value;
  if (!slug) {
    localError.value = '站点标识不可为空';
    return;
  }

  const domains = parseListInput(siteEditorForm.value.domainsText);
  if (!domains.length) {
    localError.value = '请至少填写一个域名';
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
  rateLimitPayload.enabled = !!siteEditorForm.value.rateLimitEnabled;
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

  const sitePayload = {
    label,
    domains,
    aliases,
    enabled: !!siteEditorForm.value.enabled,
    metadata: {
      nsfw: !!siteEditorForm.value.metadataNsfw,
      requires_cookies: !!siteEditorForm.value.metadataRequiresCookies,
      requires_login: !!siteEditorForm.value.metadataRequiresLogin,
      player_url_cache: !!siteEditorForm.value.metadataPlayerUrlCache,
      offline_thumbnails_download: !!siteEditorForm.value.metadataOfflineThumbnailsDownload,
      offline_thumbnails_display: !!siteEditorForm.value.metadataOfflineThumbnailsDisplay,
    },
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

  emit('save', {
    slug,
    sitePayload,
  });
};

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      siteEditorForm.value = createEmptyForm();
      localError.value = '';
      return;
    }
    hydrateForm();
  },
  { immediate: true }
);

watch(
  () => props.site,
  () => {
    if (!props.visible) return;
    hydrateForm();
  },
  { deep: true }
);
</script>

<style scoped>
.site-editor-scroll {
  scrollbar-width: thin;
  scrollbar-color: hsl(var(--muted)) transparent;
}

.site-editor-scroll::-webkit-scrollbar {
  width: 6px;
}

.site-editor-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.site-editor-scroll::-webkit-scrollbar-thumb {
  background-color: hsl(var(--muted));
  border-radius: 9999px;
}

.site-editor-scroll::-webkit-scrollbar-thumb:hover {
  background-color: hsl(var(--accent));
}

.site-editor-scroll input[type='number'] {
  -moz-appearance: textfield;
}

.site-editor-scroll input[type='number']::-webkit-outer-spin-button,
.site-editor-scroll input[type='number']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>

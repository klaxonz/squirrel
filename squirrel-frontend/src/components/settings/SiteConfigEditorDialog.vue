<template>
  <div
    v-if="visible"
    class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
  >
    <div class="bg-background border border-border/80 w-full max-w-xl rounded-lg flex flex-col max-h-[80vh] overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-border/50">
        <div class="flex items-center gap-3">
          <SiteIcon
            :icon-url="siteEditorForm.iconUrl"
            :label="siteEditorForm.label || siteEditorForm.slug"
            size="sm"
            rounded="sm"
          />
          <div>
            <h3 class="text-sm font-medium text-foreground">站点配置</h3>
            <p class="text-[11px] text-muted-foreground">{{ siteEditorForm.slug }}</p>
          </div>
        </div>
        <button
          class="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all"
          @click="$emit('close')"
        >
          <span class="text-xs">✕</span>
        </button>
      </div>

      <!-- Content -->
      <div class="site-editor-scroll flex-1 px-4 py-4 overflow-y-auto">
        
        <!-- 基本参数 -->
        <section class="mb-5">
          <h4 class="text-[11px] font-medium text-muted-foreground uppercase mb-3">基本参数</h4>
          <div class="space-y-2.5">
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0">显示名称</label>
              <Input v-model="siteEditorForm.label" placeholder="展示给用户的名称" class="flex-1 h-7 text-xs" />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0">站点别名</label>
              <Textarea v-model="siteEditorForm.aliasesText" :rows="2" placeholder="每行一个别名" class="flex-1 text-xs resize-none" />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0">域名</label>
              <Textarea
                :model-value="siteEditorForm.domainsText"
                :rows="2"
                readonly
                class="flex-1 text-xs resize-none text-muted-foreground/70"
              />
            </div>
            <div class="flex items-center justify-between py-1">
              <span class="text-xs text-foreground">启用站点</span>
              <Switch :checked="!!siteEditorForm.enabled" @update:checked="(v) => setSiteEditorBooleanField('enabled', v)" />
            </div>
          </div>
        </section>

        <!-- 采集策略 -->
        <section class="mb-5">
          <h4 class="text-[11px] font-medium text-muted-foreground uppercase mb-3">采集策略</h4>
          <div class="space-y-2.5">
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0">测试地址</label>
              <Input v-model="siteEditorForm.testUrl" placeholder="用于连通性检测的地址" class="flex-1 h-7 text-xs" />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-[11px] text-muted-foreground w-16 shrink-0">频率限制</label>
              <div class="flex items-center gap-2 flex-1">
                <Switch :checked="!!siteEditorForm.rateLimitEnabled" @update:checked="(v) => setSiteEditorBooleanField('rateLimitEnabled', v)" />
                <span v-if="siteEditorForm.rateLimitEnabled" class="flex items-center gap-1.5 text-[11px]">
                  <Input v-model="siteEditorForm.rateLimitMin" type="number" step="0.1" class="w-16 h-6 text-xs" placeholder="最小" />
                  <span class="text-muted-foreground/60">~</span>
                  <Input v-model="siteEditorForm.rateLimitMax" type="number" step="0.1" class="w-16 h-6 text-xs" placeholder="最大" />
                  <span class="text-muted-foreground/60">秒</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- 内容标记 -->
        <section>
          <h4 class="text-[11px] font-medium text-muted-foreground uppercase mb-3">内容标记</h4>
          <div class="space-y-0.5">
            <label 
              v-for="meta in [
                { key: 'metadataNsfw', label: '默认标记为敏感内容' },
                { key: 'metadataRequiresCookies', label: '需要 Cookie 才可抓取' },
                { key: 'metadataRequiresLogin', label: '需要登录状态' },
                { key: 'metadataPlayerUrlCache', label: '启用播放链接缓存' },
                { key: 'metadataOfflineThumbnailsDownload', label: '解析时下载封面到本地' },
                { key: 'metadataOfflineThumbnailsDisplay', label: '优先使用本地封面显示' }
              ]" 
              :key="meta.key"
              class="flex items-center justify-between py-1.5 px-1 rounded hover:bg-muted/40 transition-colors cursor-pointer"
            >
              <span class="text-xs text-foreground/80">{{ meta.label }}</span>
              <Switch :checked="!!siteEditorForm[meta.key]" @update:checked="(v) => setSiteEditorBooleanField(meta.key, v)" />
            </label>
          </div>
        </section>

        <Transition name="fade">
          <div v-if="resolvedError" class="mt-4 p-2.5 rounded text-destructive text-xs flex items-center gap-2">
            <AlertCircle class="h-3.5 w-3.5 shrink-0" />
            {{ resolvedError }}
          </div>
        </Transition>
      </div>

      <!-- Footer -->
      <div class="px-4 py-3 border-t border-border/50 flex items-center justify-end gap-2">
        <button 
          class="text-xs text-muted-foreground hover:text-foreground px-3 py-1.5 rounded hover:bg-muted/60 transition-all"
          @click="$emit('close')"
        >
          取消
        </button>
        <button 
          class="px-4 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-all disabled:opacity-50 flex items-center"
          :disabled="saving"
          @click="handleSave"
        >
          <Loader2 v-if="saving" class="h-3 w-3 animate-spin mr-1.5" />
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

import { AlertCircle, Loader2 } from 'lucide-vue-next'
import SiteIcon from '@/components/common/SiteIcon.vue'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
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
  iconUrl: '',
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

const setSiteEditorBooleanField = (key, value) => {
  if (!siteEditorForm.value || !key) {
    return;
  }
  siteEditorForm.value[key] = !!value;
};

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
    iconUrl: catalogInfo?.icon_url || site?.icon_url || '',
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
  const iconUrl = siteEditorForm.value.iconUrl?.trim();
  if (iconUrl) {
    sitePayload.icon_url = iconUrl;
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

watch(
  () => props.catalog,
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

.fade-enter-active, .fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-default);
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

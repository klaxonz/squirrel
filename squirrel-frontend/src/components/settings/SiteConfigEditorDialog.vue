<template>
  <div
    v-if="visible"
    class="fixed inset-0 bg-background/60 flex items-center justify-center z-50 p-4 backdrop-blur-md transition-all duration-500"
  >
    <div class="bg-background/90 border border-border/10 w-full max-w-4xl rounded-[2rem] shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
      <!-- Header: 参照 PageHeader 风格 -->
      <div class="flex items-center justify-between px-8 py-6 border-b border-border/5">
        <div class="flex items-center gap-4">
          <div class="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
            <Globe class="h-6 w-6" />
          </div>
          <div>
            <h3 class="text-xl font-black tracking-tight text-foreground">站点配置</h3>
            <p class="text-[11px] text-muted-foreground/40 mt-0.5 font-bold uppercase tracking-widest">配置标识：{{ siteEditorForm.slug }}</p>
          </div>
        </div>
        <button
          class="h-9 w-9 rounded-full bg-foreground/5 flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/10 transition-all"
          @click="$emit('close')"
        >
          <span class="text-lg">✕</span>
        </button>
      </div>

      <!-- Content: 模块化卡片布局 -->
      <div class="site-editor-scroll flex-1 px-8 py-8 space-y-10 overflow-y-auto pr-4">
        
        <!-- 第一组：基础信息 -->
        <div class="space-y-5">
          <div class="flex items-center gap-3 ml-1">
            <Settings2 class="h-4 w-4 text-primary/60" />
            <h4 class="text-[12px] font-black text-foreground/80 uppercase tracking-[0.2em]">基本参数</h4>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 rounded-[2rem] bg-card/40 border border-border/10">
            <div class="space-y-1.5 md:col-span-2">
              <Label class="text-[11px] font-bold text-muted-foreground/40 uppercase ml-1 tracking-wider">显示名称</Label>
              <Input v-model="siteEditorForm.label" placeholder="展示给用户的名称" class="bg-transparent border-border/20 focus:border-primary/40 h-11 rounded-xl transition-all" />
            </div>
            <div class="space-y-1.5">
              <Label class="text-[11px] font-bold text-muted-foreground/40 uppercase ml-1 tracking-wider">域名列表</Label>
              <Textarea v-model="siteEditorForm.domainsText" :rows="4" placeholder="每行一个域名" class="bg-transparent border-border/20 focus:border-primary/40 rounded-xl resize-none p-3.5 transition-all text-[13px]" />
            </div>
            <div class="space-y-1.5">
              <Label class="text-[11px] font-bold text-muted-foreground/40 uppercase ml-1 tracking-wider">站点别名</Label>
              <Textarea v-model="siteEditorForm.aliasesText" :rows="4" placeholder="每行一个别名" class="bg-transparent border-border/20 focus:border-primary/40 rounded-xl resize-none p-3.5 transition-all text-[13px]" />
            </div>
            
            <div class="md:col-span-2 flex items-center justify-between p-5 rounded-2xl bg-foreground/[0.03] border border-border/5 hover:border-primary/20 transition-all group">
              <div class="space-y-0.5">
                <div class="text-[13px] font-bold text-foreground group-hover:text-primary transition-colors">启用该站点</div>
                <div class="text-[11px] text-muted-foreground/40 font-medium">控制该站点是否参与自动更新与订阅采集</div>
              </div>
              <Switch :checked="!!siteEditorForm.enabled" @update:checked="(v) => siteEditorForm.enabled = !!v" />
            </div>
          </div>
        </div>

        <!-- 第二组：采集策略 -->
        <div class="space-y-5">
          <div class="flex items-center gap-3 ml-1">
            <RefreshCcw class="h-4 w-4 text-primary/60" />
            <h4 class="text-[12px] font-black text-foreground/80 uppercase tracking-[0.2em]">采集策略</h4>
          </div>
          <div class="p-6 rounded-[2rem] bg-card/40 border border-border/10 space-y-6">
            <div class="space-y-1.5">
              <Label class="text-[11px] font-bold text-muted-foreground/40 uppercase ml-1 tracking-wider">测试地址</Label>
              <Input v-model="siteEditorForm.testUrl" placeholder="用于连通性检测的地址" class="bg-transparent border-border/20 focus:border-primary/40 h-11 rounded-xl transition-all" />
            </div>
            
            <div class="space-y-5">
              <div class="flex items-center justify-between p-5 rounded-2xl bg-foreground/[0.03] border border-border/5">
                <div class="space-y-0.5">
                  <div class="text-[13px] font-bold text-foreground">频率限制</div>
                  <div class="text-[11px] text-muted-foreground/40 font-medium">开启后将按照设定的时间间隔进行反爬虫规避</div>
                </div>
                <Switch :checked="!!siteEditorForm.rateLimitEnabled" @update:checked="(v) => siteEditorForm.rateLimitEnabled = !!v" />
              </div>

              <div class="grid grid-cols-2 gap-5 transition-all duration-500" :class="!siteEditorForm.rateLimitEnabled ? 'opacity-20 grayscale pointer-events-none' : ''">
                <div class="space-y-1.5">
                  <Label class="text-[11px] font-bold text-muted-foreground/40 uppercase ml-1">最小间隔 (秒)</Label>
                  <Input v-model="siteEditorForm.rateLimitMin" type="number" step="0.1" class="bg-transparent border-border/20 h-10 rounded-xl" />
                </div>
                <div class="space-y-1.5">
                  <Label class="text-[11px] font-bold text-muted-foreground/40 uppercase ml-1">最大间隔 (秒)</Label>
                  <Input v-model="siteEditorForm.rateLimitMax" type="number" step="0.1" class="bg-transparent border-border/20 h-10 rounded-xl" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 第三组：内容与隐私 -->
        <div class="space-y-5">
          <div class="flex items-center gap-3 ml-1">
            <ShieldCheck class="h-4 w-4 text-primary/60" />
            <h4 class="text-[12px] font-black text-foreground/80 uppercase tracking-[0.2em]">内容与隐私</h4>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div 
              v-for="meta in [
                { key: 'metadataNsfw', label: '默认标记为敏感内容' },
                { key: 'metadataRequiresCookies', label: '需要 Cookie 才可抓取' },
                { key: 'metadataRequiresLogin', label: '需要登录状态' },
                { key: 'metadataPlayerUrlCache', label: '启用播放链接缓存' },
                { key: 'metadataOfflineThumbnailsDownload', label: '解析时下载封面到本地' },
                { key: 'metadataOfflineThumbnailsDisplay', label: '优先使用本地封面显示' }
              ]" 
              :key="meta.key"
              class="flex items-center justify-between p-5 rounded-2xl bg-card/40 border border-border/10 hover:border-primary/20 transition-all group"
            >
              <span class="text-[13px] font-bold text-foreground/70 group-hover:text-primary transition-colors pr-4">{{ meta.label }}</span>
              <Switch :checked="!!siteEditorForm[meta.key]" @update:checked="(v) => siteEditorForm[meta.key] = !!v" />
            </div>
          </div>
        </div>

        <Transition name="fade">
          <div v-if="resolvedError" class="p-5 rounded-2xl bg-destructive/5 border border-destructive/20 text-destructive text-[13px] font-bold flex items-center gap-4">
            <AlertCircle class="h-5 w-5" />
            {{ resolvedError }}
          </div>
        </Transition>
      </div>

      <!-- Footer: 底部操作栏 -->
      <div class="px-8 py-6 border-t border-border/5 flex items-center justify-end gap-5 bg-card/20">
        <button 
          class="text-[13px] font-bold text-muted-foreground hover:text-foreground transition-all px-4 py-2"
          @click="$emit('close')"
        >
          取消
        </button>
        <button 
          class="px-8 py-3 rounded-full bg-primary text-white text-[13px] font-black tracking-widest hover:brightness-110 shadow-lg shadow-primary/10 transition-all disabled:opacity-50 flex items-center h-11"
          :disabled="saving"
          @click="handleSave"
        >
          <Loader2 v-if="saving" class="h-4 w-4 animate-spin mr-3" />
          {{ saving ? '正在应用' : '应用配置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

import { AlertCircle, Loader2, Globe, Settings2, RefreshCcw, ShieldCheck } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Switch } from '@/components/ui/switch'
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
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

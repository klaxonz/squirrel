<template>
  <Card class="settings-card">
    <div class="px-6 py-4 border-b border-border bg-muted flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-lg font-semibold">站点配置</h2>
        <p class="text-sm text-muted-foreground">管理各站点的域名、代理与抓取参数，用于订阅与视频来源识别。</p>
      </div>
      <span class="inline-flex items-center gap-2 text-xs text-muted-foreground/70 bg-card border border-border rounded-full px-3 py-1">
        <span class="h-2 w-2 rounded-full" :class="siteSummaryDotClass"></span>
        {{ siteSummaryText }}
      </span>
    </div>

    <div class="space-y-4">
      <div v-if="siteLoading" class="px-6 py-6 text-sm text-muted-foreground">
        正在加载站点配置...
      </div>

      <div v-else>
        <div v-if="siteError" class="px-6 mb-3 text-sm text-destructive">
          {{ siteError.message || siteError }}
        </div>

        <div v-if="siteList.length === 0" class="px-6 py-6 text-sm text-muted-foreground">
          暂无站点配置。
        </div>

        <!-- 列表外框：与页面背景接近的深灰，弱化存在感 -->
        <div v-else class="site-list">
          <div class="site-list-header">
            <span>站点</span>
            <span>域名</span>
            <span class="text-right">状态</span>
          </div>
          <div class="site-list-body">
            <div
              v-for="site in siteList"
              :key="site.slug"
              class="site-list-item"
            >
              <div class="site-list-main">
                <div class="site-title">
                  <span class="font-medium">{{ site.label }}</span>
                  <span class="text-xs text-muted-foreground/70">({{ site.slug }})</span>
                </div>
                <div class="site-domain">
                  <span v-if="site.domains && site.domains.length">{{ site.domains.join(', ') }}</span>
                  <span v-else class="italic">未配置</span>
                </div>
              </div>
              <div class="site-list-meta">
                <span
                  class="site-status"
                  :class="site.enabled ? 'bg-emerald-500/10 text-emerald-500' : 'bg-muted text-muted-foreground'"
                >
                  {{ site.enabled ? '已启用' : '已禁用' }}
                </span>
                <button
                  class="site-table-action"
                  @click="openSiteEditor(site)"
                >
                  配置
                </button>
              </div>
            </div>
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
  </Card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useSiteCatalog } from '@/composables/useSites';
import { Card } from '@/components/ui/card';
import SiteConfigEditorDialog from '@/components/settings/SiteConfigEditorDialog.vue';
import { Logger } from '@/utils/logger'

const { catalog: siteCatalog, loading: siteLoading, error: siteError, loadCatalog, saveCatalog } = useSiteCatalog();

const editingSite = ref(null);
const siteEditorVisible = ref(false);
const siteEditorSaving = ref(false);
const siteEditorError = ref('');

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

const siteSummaryText = computed(() => {
  if (siteLoading.value) return '加载中';
  if (siteError.value) return '加载失败';
  if (!siteList.value.length) return '暂无站点';
  return `${siteList.value.length} 个站点`;
});

const siteSummaryDotClass = computed(() => {
  if (siteLoading.value) return 'bg-blue-500 animate-pulse';
  if (siteError.value) return 'bg-destructive animate-pulse';
  if (!siteList.value.length) return 'bg-muted';
  return 'bg-emerald-500';
});

onMounted(async () => {
  await loadCatalog();
});

const openSiteEditor = (site) => {
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
</script>

<style scoped>
.settings-card {
  @apply rounded-2xl shadow-sm;
  background-color: hsl(var(--card));
  background-color: color-mix(in srgb, hsl(var(--card)) 60%, hsl(var(--background)));
}

.site-list {
  @apply border border-border rounded-none overflow-hidden bg-background;
}

.site-list-header {
  @apply hidden sm:grid sm:grid-cols-[2.2fr_2.8fr_1fr] px-6 py-2 text-xs text-muted-foreground/70 bg-muted;
}

.site-list-body {
  @apply divide-y divide-border;
}

.site-list-item {
  @apply flex flex-col gap-3 px-6 py-4 text-sm hover:bg-accent transition-colors sm:flex-row sm:items-center sm:justify-between;
}

.site-list-main {
  @apply flex flex-col gap-2 min-w-0 sm:flex-row sm:items-center sm:gap-6 sm:flex-1;
}

.site-title {
  @apply flex items-center gap-2 min-w-0 sm:min-w-[12rem];
}

.site-domain {
  @apply text-sm text-muted-foreground truncate;
}

.site-list-meta {
  @apply flex items-center justify-between gap-3 sm:justify-end sm:min-w-[10rem];
}

.site-status {
  @apply px-2 py-0.5 rounded-full text-xs font-medium;
}

.site-table-action {
  @apply px-3 py-1.5 bg-muted hover:bg-accent rounded-full text-xs font-medium transition-colors border border-border text-foreground;
}
</style>

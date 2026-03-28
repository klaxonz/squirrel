<template>
  <div class="settings-section slide-up">
    <div class="settings-section-header">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold tracking-tight text-foreground">采集源配置</h2>
        <div class="text-[11px] font-black text-muted-foreground/20 uppercase tracking-[0.2em]">
          {{ siteSummaryText }}
        </div>
      </div>
    </div>

    <div class="settings-section-content mt-10">
      <div v-if="siteLoading" class="py-12 flex flex-col items-center justify-center gap-3">
        <Loader2 class="h-5 w-5 animate-spin text-muted-foreground/10" />
      </div>

      <div v-else>
        <div v-if="siteError" class="mb-6 p-4 rounded-xl border border-destructive/20 bg-destructive/5 text-[13px] text-destructive flex items-center gap-3">
          <AlertCircle class="h-4 w-4 shrink-0" />
          {{ siteError.message || siteError }}
        </div>

        <div v-if="siteList.length === 0" class="py-16 text-center border-2 border-dashed border-border/40 rounded-2xl">
          <Globe class="h-6 w-6 mx-auto text-muted-foreground/10" />
          <p class="mt-3 text-xs text-muted-foreground/30 font-medium">未发现可用站点配置</p>
        </div>

        <div v-else class="site-grid grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            v-for="site in siteList"
            :key="site.slug"
            class="site-item group p-4 rounded-2xl border border-border/40 bg-muted/[0.04] hover:bg-muted/[0.1] hover:border-border/60 transition-all duration-300"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="flex items-center gap-3">
                  <div class="h-8 w-8 rounded-xl bg-background border border-border/40 flex items-center justify-center shadow-sm shrink-0 transition-transform group-hover:scale-105">
                    <span class="text-[11px] font-black text-muted-foreground/40">{{ site.slug.substring(0, 2).toUpperCase() }}</span>
                  </div>
                  <div class="min-w-0">
                    <div class="text-[14px] font-bold text-foreground tracking-tight truncate">{{ site.label }}</div>
                    <div class="text-[11px] text-muted-foreground/30 font-medium mt-0.5 uppercase">{{ site.slug }}</div>
                  </div>
                </div>
              </div>

              <div class="flex flex-col items-end gap-2 shrink-0">
                <div
                  class="h-1 w-1 rounded-full"
                  :class="site.enabled ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-muted-foreground/10'"
                ></div>
                <button
                  class="text-[11px] font-bold text-primary/40 hover:text-primary transition-colors mt-3"
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { 
  Loader2, 
  Globe, 
  AlertCircle, 
  Settings2,
  ExternalLink
} from 'lucide-vue-next';
import { useSiteCatalog } from '@/composables/useSites';
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
.site-item {
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}

.site-item:hover {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}
</style>

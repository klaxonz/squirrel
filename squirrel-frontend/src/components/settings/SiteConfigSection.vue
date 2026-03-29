<template>
  <div class="settings-section slide-up">
    <div class="settings-section-header">
      <div class="flex items-end justify-between">
        <div class="min-w-0">
          <h2 class="text-2xl font-black tracking-tight text-foreground">采集源配置</h2>
          <p class="text-[13px] text-muted-foreground/50 mt-1 font-medium italic">配置与管理各站点的采集参数。</p>
        </div>
        <div class="text-[11px] font-black text-muted-foreground/20 uppercase tracking-[0.2em] pb-1">
          {{ siteSummaryText }}
        </div>
      </div>
    </div>

    <div class="settings-section-content mt-12">
      <div v-if="siteLoading" class="py-12 flex flex-col items-center justify-center gap-3">
        <Loader2 class="h-6 w-6 animate-spin text-primary/20" />
      </div>

      <div v-else>
        <div v-if="siteError" class="mb-8 p-5 rounded-2xl border border-destructive/20 bg-destructive/5 text-[13px] text-destructive flex items-center gap-4">
          <AlertCircle class="h-5 w-5 shrink-0" />
          <span class="font-bold">{{ siteError.message || siteError }}</span>
        </div>

        <div v-if="siteList.length === 0" class="py-20 text-center border-2 border-dashed border-border/20 rounded-[32px] bg-muted/[0.02]">
          <Globe class="h-8 w-8 mx-auto text-muted-foreground/10" />
          <p class="mt-4 text-[13px] text-muted-foreground/30 font-bold uppercase tracking-widest">未发现可用站点配置</p>
        </div>

        <div v-else class="site-grid grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="site in siteList"
            :key="site.slug"
            class="site-item group p-5 rounded-[24px] border border-border/40 bg-muted/[0.02] hover:bg-muted/[0.06] hover:border-primary/20 hover:shadow-xl hover:shadow-primary/[0.02] transition-all duration-500"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="flex items-center gap-4">
                  <div class="h-10 w-10 rounded-2xl bg-background border border-border/40 flex items-center justify-center shadow-sm shrink-0 transition-all duration-500 group-hover:scale-110 group-hover:rotate-[-5deg] group-hover:border-primary/20">
                    <span class="text-[12px] font-black text-muted-foreground/40 group-hover:text-primary/60">{{ site.slug.substring(0, 2).toUpperCase() }}</span>
                  </div>
                  <div class="min-w-0">
                    <div class="text-[15px] font-black text-foreground tracking-tight truncate">{{ site.label }}</div>
                    <div class="text-[11px] text-muted-foreground/30 font-bold mt-0.5 uppercase tracking-wider">{{ site.slug }}</div>
                  </div>
                </div>
              </div>

              <div class="flex flex-col items-end justify-between h-10 shrink-0">
                <div
                  class="h-1.5 w-1.5 rounded-full transition-all duration-500"
                  :class="site.enabled ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)] scale-110' : 'bg-muted-foreground/10'"
                ></div>
                <button
                  class="text-[11px] font-black text-primary/30 hover:text-primary transition-all uppercase tracking-widest"
                  @click="openSiteEditor(site)"
                >
                  Configure
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
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.02);
}

.site-item:hover {
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.05), 0 8px 10px -6px rgb(0 0 0 / 0.05);
}
</style>

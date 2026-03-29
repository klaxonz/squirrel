<template>
  <div class="settings-section slide-up">
    <div class="settings-section-header">
      <div class="flex items-end justify-between">
        <div class="min-w-0">
          <h2 class="text-3xl font-bold tracking-tighter text-foreground uppercase">采集源配置</h2>
          <p class="text-[11px] text-muted-foreground/30 mt-2 font-bold uppercase tracking-widest">SOURCE CATALOG & EXTRACTION PARAMETERS</p>
        </div>
        <div class="text-[10px] font-black text-muted-foreground/10 uppercase tracking-[0.3em] pb-1">
          {{ siteSummaryText }}
        </div>
      </div>
    </div>

    <div class="settings-section-content mt-12 border-t border-border/5">
      <div v-if="siteLoading" class="py-12 flex flex-col items-center justify-center gap-3">
        <Loader2 class="h-6 w-6 animate-spin text-primary/20" />
      </div>

      <div v-else>
        <div v-if="siteError" class="mb-8 p-5 rounded-2xl border border-destructive/20 bg-destructive/5 text-[13px] text-destructive flex items-center gap-4">
          <AlertCircle class="h-5 w-5 shrink-0" />
          <span class="font-bold">{{ siteError.message || siteError }}</span>
        </div>

        <div v-if="siteList.length === 0" class="py-20 text-center border border-dashed border-border/10">
          <Globe class="h-8 w-8 mx-auto text-muted-foreground/10" />
          <p class="mt-4 text-[11px] text-muted-foreground/20 font-bold uppercase tracking-widest">NO SOURCE DETECTED</p>
        </div>

        <div v-else class="site-grid grid grid-cols-1 md:grid-cols-2">
          <div
            v-for="site in siteList"
            :key="site.slug"
            class="site-item group p-8 border-b border-border/5 md:odd:border-r transition-all duration-700 relative overflow-hidden"
          >
            <div class="flex items-start justify-between gap-6 relative z-10">
              <div class="min-w-0">
                <div class="flex items-center gap-6">
                  <div class="h-12 w-12 border border-border/10 flex items-center justify-center shrink-0 transition-all duration-700 group-hover:rotate-90 group-hover:border-primary/40">
                    <span class="text-[11px] font-black text-muted-foreground/20 group-hover:text-primary/60">{{ site.slug.substring(0, 2).toUpperCase() }}</span>
                  </div>
                  <div class="min-w-0 transition-transform duration-500 group-hover:translate-x-2">
                    <div class="text-[14px] font-bold text-foreground tracking-widest uppercase truncate">{{ site.label }}</div>
                    <div class="text-[10px] text-muted-foreground/20 font-bold mt-1 uppercase tracking-[0.2em]">{{ site.slug }}</div>
                  </div>
                </div>
              </div>

              <div class="flex flex-col items-end justify-between h-12 shrink-0">
                <div
                  class="h-1 w-1 rounded-full transition-all duration-700"
                  :class="site.enabled ? 'bg-primary' : 'bg-muted-foreground/10'"
                ></div>
                <button
                  class="text-[10px] font-black text-muted-foreground/30 hover:text-primary transition-all uppercase tracking-widest"
                  @click="openSiteEditor(site)"
                >
                  Configure
                </button>
              </div>
            </div>
            
            <div class="absolute inset-0 bg-primary/[0.01] translate-y-full group-hover:translate-y-0 transition-transform duration-700"></div>
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
.slide-up {
  animation: slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.99);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>

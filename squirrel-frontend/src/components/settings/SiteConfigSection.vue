<template>
  <div class="settings-section slide-up">
    <div class="settings-section-header">
      <div class="flex items-end justify-between">
        <div class="min-w-0">
          <h2 class="text-3xl font-bold tracking-tighter text-foreground">采集源配置</h2>
          <p class="text-[11px] text-muted-foreground/30 mt-2 font-bold tracking-wide">源目录与采集参数</p>
        </div>
        <div class="text-[10px] font-black text-muted-foreground/10 tracking-[0.1em] pb-1">
          {{ siteSummaryText }}
        </div>
      </div>
    </div>

    <div class="settings-section-content mt-12">
      <div v-if="siteLoading" class="py-20 flex flex-col items-center justify-center gap-4 bg-card/30 rounded-[2rem] border border-border/5">
        <Loader2 class="h-8 w-8 animate-spin text-primary/40" />
        <p class="text-[11px] text-muted-foreground/30 font-bold uppercase tracking-widest">正在同步站点元数据</p>
      </div>

      <div v-else>
        <div v-if="siteError" class="mb-8 p-6 rounded-[1.5rem] border border-destructive/20 bg-destructive/5 text-[13px] text-destructive flex items-center gap-4">
          <AlertCircle class="h-5 w-5 shrink-0" />
          <span class="font-bold">{{ siteError.message || siteError }}</span>
        </div>

        <div v-if="siteList.length === 0" class="py-24 text-center bg-card/30 rounded-[2rem] border border-dashed border-border/10">
          <Globe class="h-10 w-10 mx-auto text-muted-foreground/10" />
          <p class="mt-4 text-[11px] text-muted-foreground/20 font-bold tracking-wide">未发现可用站点</p>
        </div>

        <div v-else class="site-grid grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="site in siteList"
            :key="site.slug"
            class="site-item group p-6 rounded-[2rem] bg-card/30 border border-border/5 hover:border-primary/20 hover:bg-card/50 transition-all duration-500 relative overflow-hidden"
          >
            <div class="flex items-start justify-between gap-6 relative z-10">
              <div class="min-w-0">
                <div class="flex items-center gap-4">
                  <SiteIcon
                    :icon-url="site.iconUrl"
                    :label="site.label"
                    size="lg"
                    rounded="md"
                    class="h-14 w-14 rounded-2xl bg-background/40 border border-border/10 transition-all duration-700 group-hover:rotate-[10deg] group-hover:border-primary/40 group-hover:bg-primary/5"
                  />
                  <div class="min-w-0 transition-transform duration-500 group-hover:translate-x-1">
                    <div class="text-[15px] font-bold text-foreground tracking-tight truncate group-hover:text-primary transition-colors">{{ site.label }}</div>
                    <div class="text-[11px] text-muted-foreground/30 font-bold mt-0.5 tracking-wider">{{ site.slug }}</div>
                  </div>
                </div>
              </div>

              <div class="flex flex-col items-end justify-between h-14 shrink-0">
                <div
                  class="h-2 w-2 rounded-full transition-all duration-700 shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)]"
                  :class="site.enabled ? 'bg-primary scale-110' : 'bg-muted-foreground/10 scale-100'"
                ></div>
                <button
                  class="px-5 py-2 rounded-full bg-foreground/[0.03] border border-border/5 text-[11px] font-black uppercase tracking-widest text-muted-foreground/50 hover:text-primary hover:border-primary/20 hover:bg-primary/5 transition-all"
                  @click="openSiteEditor(site)"
                >
                  配置
                </button>
              </div>
            </div>
            
            <div class="absolute inset-0 bg-primary/[0.02] opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
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
  AlertCircle
} from 'lucide-vue-next';
import { useSiteCatalog } from '@/composables/useSites';
import SiteIcon from '@/components/common/SiteIcon.vue';
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
    iconUrl: info?.icon_url || '',
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

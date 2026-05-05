<template>
  <Dialog :open="show" @update:open="handleOpenChange">
    <DialogScrollContent class="max-w-4xl gap-0 overflow-hidden p-0">
      <div class="import-dialog__hero">
        <DialogHeader class="space-y-2 px-6 pb-4 pt-6">
          <DialogTitle class="text-xl font-semibold tracking-[-0.03em]">导入订阅</DialogTitle>
          <DialogDescription class="leading-6">
            从站点读取已有订阅并选择要同步进来的频道。
          </DialogDescription>
        </DialogHeader>
      </div>

      <div class="space-y-6 px-6 py-5">
        <section v-if="step === 1" class="space-y-5">
          <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
            <button
              v-for="site in supportedSites"
              :key="site"
              type="button"
              :class="[
                'import-dialog__site-card',
                selectedSite === site && 'import-dialog__site-card--active',
              ]"
              @click="selectedSite = site"
            >
              <SiteIcon
                :icon-url="getSiteIconUrl(site)"
                :label="getSiteName(site)"
                size="lg"
                class="import-dialog__site-icon"
              />
              <span class="import-dialog__site-name">{{ getSiteName(site) }}</span>
            </button>
          </div>

          <Alert v-if="requestError">
            <AlertDescription>{{ requestError }}</AlertDescription>
          </Alert>
        </section>

        <section v-else-if="step === 2" class="space-y-4">
          <div class="import-dialog__summary">
            <div class="import-dialog__summary-block">
              <span class="import-dialog__summary-label">进度</span>
              <strong class="import-dialog__summary-value">{{ loadedCount }}</strong>
              <p class="mt-1 text-xs text-muted-foreground">已加载 {{ loadedCount }} / {{ previewData.total ?? '未知' }} 个</p>
            </div>
            <div class="import-dialog__summary-block">
              <span class="import-dialog__summary-label">已导入</span>
              <strong class="import-dialog__summary-value">{{ importedCount }}</strong>
            </div>
            <div class="import-dialog__summary-block">
              <span class="import-dialog__summary-label">未导入</span>
              <strong class="import-dialog__summary-value">{{ notImportedCount }}</strong>
            </div>
            <div class="import-dialog__summary-block">
              <span class="import-dialog__summary-label">已选</span>
              <strong class="import-dialog__summary-value">{{ selectedCount }}</strong>
            </div>
          </div>

          <div v-if="loadingPreview && !loadedCount" class="import-dialog__loader">
            <AppIcon name="loadingSpinner" class="h-6 w-6 animate-spin text-primary" />
            <span class="text-sm text-muted-foreground">正在读取订阅列表...</span>
          </div>

          <template v-else>
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="secondary" class="rounded-full" @click="selectAllNotImported">全选已加载未导入</Button>
                <Button size="sm" variant="ghost" class="rounded-full" @click="clearSelection">清空</Button>
              </div>
              <p class="text-sm text-muted-foreground">
                已加载 {{ loadedCount }} / {{ previewData.total ?? '未知' }} 个
                <span v-if="previewData.has_more">，可继续加载</span>
              </p>
            </div>

            <Alert v-if="requestError">
              <AlertDescription>{{ requestError }}</AlertDescription>
            </Alert>

            <div class="import-dialog__list">
              <label
                v-for="sub in previewData.subscriptions"
                :key="sub.url"
                :class="[
                  'import-dialog__list-item',
                  sub.is_imported && 'import-dialog__list-item--disabled',
                  selectedUrlMap[sub.url] && !sub.is_imported && 'import-dialog__list-item--selected',
                ]"
              >
                <input
                  type="checkbox"
                  class="import-dialog__checkbox"
                  :disabled="sub.is_imported"
                  :checked="!!selectedUrlMap[sub.url]"
                  @change="toggleSelection(sub)"
                />

                <img
                  :src="getAvatarSrc(sub.avatar, sub.url)"
                  class="import-dialog__avatar"
                  alt="avatar"
                  referrerpolicy="no-referrer"
                  @error="(event) => handleAvatarError(event, sub.url)"
                />

                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-medium text-foreground">{{ sub.name || '未命名订阅' }}</p>
                  <p class="truncate text-xs text-muted-foreground">{{ sub.url }}</p>
                </div>

                <Badge :variant="sub.is_imported ? 'secondary' : 'outline'" class="rounded-full">
                  {{ sub.is_imported ? '已导入' : '未导入' }}
                </Badge>
              </label>
            </div>

            <div v-if="previewData.has_more" class="flex justify-center pt-2">
              <Button size="sm" variant="outline" :disabled="loadingMorePreview" @click="loadMorePreview">
                <AppIcon v-if="loadingMorePreview" name="loadingSpinner" class="h-4 w-4 animate-spin" />
                {{ loadingMorePreview ? '加载中...' : '加载更多' }}
              </Button>
            </div>
          </template>
        </section>

        <section v-else-if="step === 3" class="space-y-5 py-3">
          <div class="import-dialog__result-icon">
            <AppIcon name="check" class="h-8 w-8 text-emerald-500" />
          </div>

          <div class="text-center">
            <h3 class="text-2xl font-bold tracking-[-0.04em] text-foreground">
              {{ importResult.total > 0 ? '任务已提交' : '没有需要导入的订阅' }}
            </h3>
            <p class="mt-2 text-sm text-muted-foreground">
              {{ importResult.total > 0 ? '后台已经开始处理导入任务。' : '当前没有符合条件的订阅。' }}
            </p>
          </div>

          <div class="import-dialog__result-card">
            <p class="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">新增导入任务</p>
            <p class="mt-2 text-4xl font-bold tracking-[-0.05em] text-foreground">{{ importResult.total || 0 }}</p>
            <p class="mt-3 text-xs text-muted-foreground">
              <span v-if="importResult.found != null">
                拉取 {{ importResult.found }} 个，选择 {{ importResult.selected ?? 0 }} 个，跳过 {{ importResult.skipped ?? 0 }} 个。
              </span>
              <span v-else>
                选择 {{ importResult.selected ?? 0 }} 个，跳过 {{ importResult.skipped ?? 0 }} 个。
              </span>
            </p>
          </div>

          <Alert>
            <AlertDescription>
              <span v-if="importResult.total > 0">
                导入任务已提交，处理完成后订阅列表会自动更新。
              </span>
              <span v-else>
                可能都已导入，或者当前没有勾选任何未导入项。
              </span>
            </AlertDescription>
          </Alert>
        </section>
      </div>

      <DialogFooter class="border-t border-border/70 bg-secondary/24 px-6 py-4 sm:justify-end">
        <Button v-if="step === 1" size="sm" variant="ghost" :disabled="loadingPreview" @click="handleClose">取消</Button>
        <Button v-if="step === 1" size="sm" :disabled="!selectedSite || loadingPreview" @click="handlePreview">
          <AppIcon v-if="loadingPreview" name="loadingSpinner" class="h-4 w-4 animate-spin" />
          预览订阅
        </Button>

        <Button v-if="step === 2" size="sm" variant="ghost" :disabled="importing" @click="step = 1">返回</Button>
        <Button
          v-if="step === 2"
          size="sm"
          :disabled="importing || selectedCount === 0"
          @click="handleImport"
        >
          <AppIcon v-if="importing" name="loadingSpinner" class="h-4 w-4 animate-spin" />
          {{ importing ? '导入中...' : `确认导入 (${selectedCount})` }}
        </Button>

        <Button v-if="step === 3" size="sm" @click="handleClose">完成</Button>
      </DialogFooter>
    </DialogScrollContent>
  </Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import {
  getSupportedImportSites,
  importSubscriptions,
  previewImportSubscriptions,
} from '@/api'
import SiteIcon from '@/components/common/SiteIcon.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/components/ui/dialog'
import { useImageFallback } from '@/composables/useImageFallback'
import { useSiteCatalog } from '@/composables/useSites'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'imported'])
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const { catalog: siteCatalog, loadCatalog } = useSiteCatalog()

const step = ref(1)
const supportedSites = ref([])
const selectedSite = ref('')
const PREVIEW_BATCH_SIZE = 50
const previewData = ref({
  total: null,
  subscriptions: [],
  has_more: false,
  cursor_payload: null,
})
const selectedUrlMap = ref({})
const importResult = ref({})
const loadingPreview = ref(false)
const loadingMorePreview = ref(false)
const importing = ref(false)
const requestError = ref('')

const siteConfig = {
  bilibili: { name: '哔哩哔哩' },
  youtube: { name: '油管' },
  pornhub: { name: '成人站点一' },
  youporn: { name: '成人站点二' },
  javdb: { name: '影片数据库' },
}

const getSiteCatalogItem = (site) => siteCatalog.value?.[site?.toLowerCase?.() || site] || null
const getSiteName = (site) => getSiteCatalogItem(site)?.label || siteConfig[site]?.name || site.charAt(0).toUpperCase() + site.slice(1)
const getSiteIconUrl = (site) => {
  const iconUrl = getSiteCatalogItem(site)?.icon_url
  return typeof iconUrl === 'string' && iconUrl.trim() ? iconUrl : null
}
const selectedCount = computed(() => Object.keys(selectedUrlMap.value || {}).length)
const loadedCount = computed(() => (previewData.value.subscriptions || []).length)
const importedCount = computed(() => (
  previewData.value.subscriptions || []
).filter(item => item?.is_imported).length)
const notImportedCount = computed(() => (
  previewData.value.subscriptions || []
).filter(item => item && !item.is_imported).length)

const resetState = () => {
  step.value = 1
  selectedSite.value = ''
  previewData.value = {
    total: null,
    subscriptions: [],
    has_more: false,
    cursor_payload: null,
  }
  selectedUrlMap.value = {}
  importResult.value = {}
  loadingMorePreview.value = false
  requestError.value = ''
}

const selectAllNotImported = () => {
  const map = {}
  for (const sub of previewData.value.subscriptions || []) {
    if (sub?.url && !sub.is_imported) {
      map[sub.url] = true
    }
  }
  selectedUrlMap.value = map
}

const clearSelection = () => {
  selectedUrlMap.value = {}
}

const toggleSelection = (sub) => {
  if (!sub?.url || sub.is_imported) return

  const map = { ...(selectedUrlMap.value || {}) }
  if (map[sub.url]) {
    delete map[sub.url]
  } else {
    map[sub.url] = true
  }
  selectedUrlMap.value = map
}

const loadSupportedSites = async () => {
  await loadCatalog()
  const { data, error } = await getSupportedImportSites()
  if (error) {
    requestError.value = error.message || '加载可导入站点失败'
    supportedSites.value = []
    return
  }
  requestError.value = ''
  supportedSites.value = data
}

const mergePreviewSubscriptions = (existing, incoming) => {
  const merged = []
  const seen = new Set()
  for (const item of [...(existing || []), ...(incoming || [])]) {
    if (!item?.url || seen.has(item.url)) continue
    seen.add(item.url)
    merged.push(item)
  }
  return merged
}

const fetchPreviewBatch = async ({ cursorPayload = null, append = false } = {}) => {
  const loadingState = append ? loadingMorePreview : loadingPreview
  loadingState.value = true
  const result = await previewImportSubscriptions(selectedSite.value, {
    cursorPayload,
    limit: PREVIEW_BATCH_SIZE,
  })
  loadingState.value = false

  if (!result.error) {
    requestError.value = ''
    previewData.value = {
      total: result.data?.total ?? previewData.value.total,
      subscriptions: append
        ? mergePreviewSubscriptions(previewData.value.subscriptions, result.data?.subscriptions || [])
        : (result.data?.subscriptions || []),
      has_more: !!result.data?.has_more,
      cursor_payload: result.data?.cursor_payload || null,
    }
    return true
  }
  requestError.value = result.error.message || '预览订阅失败'
  return false
}

const handlePreview = async () => {
  if (!selectedSite.value) return

  requestError.value = ''
  const loaded = await fetchPreviewBatch()
  if (loaded) {
    selectAllNotImported()
    step.value = 2
  }
}

const loadMorePreview = async () => {
  if (!selectedSite.value || !previewData.value.has_more) return
  await fetchPreviewBatch({
    cursorPayload: previewData.value.cursor_payload,
    append: true,
  })
}

const handleImport = async () => {
  if (!selectedSite.value) return

  importing.value = true
  requestError.value = ''
  const subscriptionUrls = Object.keys(selectedUrlMap.value || {})
  const result = await importSubscriptions(selectedSite.value, subscriptionUrls)
  importing.value = false

  if (!result.error) {
    requestError.value = ''
    importResult.value = result.data
    step.value = 3
    return
  }
  requestError.value = result.error.message || '导入订阅失败'
}

const handleClose = () => {
  emit('close')
  if (step.value === 3 && importResult.value.total > 0) {
    emit('imported')
  }
  setTimeout(resetState, 200)
}

const handleOpenChange = (open) => {
  if (!open) {
    handleClose()
  }
}

watch(() => props.show, (visible) => {
  if (visible) {
    loadSupportedSites()
  } else {
    resetState()
  }
})
</script>

<style scoped>
.import-dialog__hero {
  background:
    radial-gradient(circle at top right, hsl(var(--primary) / 0.12), transparent 38%),
    linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--background) / 0.92));
}

.import-dialog__site-card {
  display: grid;
  gap: 0.8rem;
  place-items: center;
  padding: 1.2rem 0.9rem;
  border: 1px solid hsl(var(--border) / 0.76);
  border-radius: calc(var(--radius-xl) + 2px);
  background: hsl(var(--card) / 0.84);
  transition:
    transform var(--duration-normal) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.import-dialog__site-card:hover {
  transform: translateY(-2px);
  border-color: hsl(var(--primary) / 0.24);
}

.import-dialog__site-card--active {
  border-color: hsl(var(--primary) / 0.4);
  background: hsl(var(--primary) / 0.08);
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.14);
}

.import-dialog__site-icon {
  display: inline-flex;
  width: 3.15rem;
  height: 3.15rem;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
  font-size: 1.25rem;
  font-weight: 700;
}

.import-dialog__site-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.import-dialog__summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.import-dialog__summary-block {
  padding: 0.85rem 0.95rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1rem;
  background: hsl(var(--card) / 0.82);
}

.import-dialog__summary-label {
  display: block;
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

.import-dialog__summary-value {
  display: block;
  margin-top: 0.2rem;
  font-size: 1.15rem;
  color: hsl(var(--foreground));
}

.import-dialog__loader {
  display: flex;
  min-height: 12rem;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.85rem;
}

.import-dialog__list {
  display: grid;
  gap: 0.55rem;
  max-height: 24rem;
  overflow-y: auto;
  padding-right: 0.15rem;
}

.import-dialog__list-item {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.85rem 0.9rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1rem;
  background: hsl(var(--card) / 0.8);
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.import-dialog__list-item--selected {
  border-color: hsl(var(--primary) / 0.3);
  background: hsl(var(--primary) / 0.05);
}

.import-dialog__list-item--disabled {
  opacity: 0.78;
}

.import-dialog__checkbox {
  width: 1rem;
  height: 1rem;
  accent-color: hsl(var(--primary));
}

.import-dialog__avatar {
  width: 2.15rem;
  height: 2.15rem;
  border-radius: calc(var(--radius-sm) - 1px);
  object-fit: cover;
}

.import-dialog__result-icon {
  display: flex;
  width: 4rem;
  height: 4rem;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  border-radius: 9999px;
  background: hsl(145 63% 92%);
}

.dark .import-dialog__result-icon {
  background: hsl(145 44% 18%);
}

.import-dialog__result-card {
  padding: 1.4rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1.25rem;
  background:
    radial-gradient(circle at top left, hsl(var(--primary) / 0.08), transparent 36%),
    linear-gradient(180deg, hsl(var(--card) / 0.96), hsl(var(--background) / 0.92));
  text-align: center;
}

@media (min-width: 768px) {
  .import-dialog__summary {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>

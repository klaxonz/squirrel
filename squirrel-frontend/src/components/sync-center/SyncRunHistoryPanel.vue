<template>
  <div class="flex min-h-0 flex-col overflow-hidden" :class="embedded ? 'h-full' : ''">
    <div
      class="border-b border-border/40 pb-4"
    >
      <div v-if="embedded" class="space-y-4">
        <div class="flex items-center justify-between gap-3 px-1">
          <div class="space-y-0.5">
            <h2 class="text-sm font-semibold tracking-tight text-foreground/90">运行实例</h2>
          </div>
          <div class="flex items-center gap-3">
            <slot name="header-action" />
            <span class="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/30">
              {{ total }} 项 · {{ page }} / {{ totalPages }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-1.5 rounded-xl border border-border/40 bg-muted/10 p-1">
          <div class="w-full sm:w-[8rem]">
            <Select :model-value="draftFilters.status" @update:model-value="(value) => updateDraftFilter('status', String(value ?? ''))">
              <SelectTrigger class="h-8 border-none bg-transparent text-[11px] font-semibold text-muted-foreground/80 focus:ring-0">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="mx-0.5 h-3.5 w-px bg-border/40"></div>

          <div class="w-full sm:w-[8rem]">
            <Select :model-value="draftFilters.site" @update:model-value="(value) => updateDraftFilter('site', String(value ?? ''))">
              <SelectTrigger class="h-8 border-none bg-transparent text-[11px] font-semibold text-muted-foreground/80 focus:ring-0">
                <SelectValue placeholder="站点" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in siteOptions" :key="option.value" :value="option.value">
                  <div class="flex items-center gap-2">
                    <SiteIcon
                      v-if="option.value"
                      :icon-url="option.iconUrl"
                      :label="option.label"
                      size="xs"
                    />
                    <span>{{ option.label }}</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="mx-0.5 h-3.5 w-px bg-border/40"></div>

          <div class="w-full sm:w-[12rem]">
            <SyncSubscriptionSelect size="xs" :model-value="draftFilters.subscriptionId" :options="subscriptionOptions" @update:model-value="(value) => updateDraftFilter('subscriptionId', String(value || ''))" />
          </div>

          <div class="mx-0.5 h-3.5 w-px bg-border/40"></div>

          <div class="flex-1 sm:max-w-[12rem]">
            <Popover>
              <PopoverTrigger as-child>
                <button
                   class="flex h-8 w-full items-center gap-2 px-3 text-left text-[11px] font-semibold text-muted-foreground transition-colors hover:text-foreground focus:outline-none"
                >
                  <CalendarIcon class="h-3.5 w-3.5 opacity-50" />
                  <span v-if="dateRangeLabel" class="truncate">{{ dateRangeLabel }}</span>
                  <span v-else class="truncate opacity-50">日期范围</span>
                </button>
              </PopoverTrigger>
              <PopoverContent class="w-auto p-0" align="start">
                <div class="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
                  <div class="text-2xs text-muted-foreground">选择范围</div>
                  <Button variant="ghost" size="xs" class="h-7 px-2" @click="clearDateRange">清除</Button>
                </div>
                <RangeCalendar
                  :model-value="dateRange"
                  :number-of-months="2"
                  locale="zh-CN"
                  @update:model-value="handleDateRangeUpdate"
                />
              </PopoverContent>
            </Popover>
          </div>

          <div class="ml-auto flex items-center pr-1">
            <Button variant="ghost" size="xs" class="h-7 w-7 p-0 text-muted-foreground/60 hover:text-foreground" :disabled="loading" @click="applyFilters">
              <Search class="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="px-1 py-3 text-xs text-destructive/80">{{ error }}</div>
    <div v-if="loading" class="flex-1 py-12">
      <SyncBoardSkeleton :count="8" />
    </div>
    <div v-else-if="runs.length === 0" class="flex-1 py-12">
      <SyncBoardEmpty 
        title="INSTANCE_EMPTY"
        message="未找到符合条件的运行实例" 
      />
    </div>

    <div v-else class="flex-1 overflow-auto pt-4">
      <table class="w-full min-w-[1000px] text-[12px]">
        <thead>
          <tr class="text-[10px] uppercase tracking-[0.15em] text-muted-foreground/40 border-b border-border/40">
            <th class="px-3 py-4 text-left font-bold">订阅</th>
            <th class="px-3 py-4 text-left font-bold">状态</th>
            <th class="px-3 py-4 text-left font-bold">详情</th>
            <th class="px-3 py-4 text-left font-bold">时间</th>
            <th class="px-3 py-4 text-left font-bold">产出</th>
            <th class="px-3 py-4 text-right font-bold pr-6">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/10">
          <tr
            v-for="run in runs"
            :key="run.run_id"
            class="group cursor-pointer transition-all hover:bg-muted/50"
            :class="selectedRunId === run.run_id ? 'bg-muted shadow-[inset_3px_0_0_0_theme(colors.blue.500)]' : ''"
            @click="emit('open-run', run.run_id)"
          >
            <td class="px-3 py-4 align-middle">
              <div class="flex items-center gap-3">
                <img
                  :src="getAvatarSrc(run.subscription_avatar, getAvatarKey(run))"
                  :alt="run.subscription_name"
                  class="h-7 w-7 rounded-lg object-cover ring-1 ring-border/40"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, getAvatarKey(run))"
                >
                <div class="flex flex-col gap-0.5">
                  <span class="font-bold text-foreground/80 truncate max-w-[14rem]">{{ run.subscription_name }}</span>
                  <span class="text-[10px] font-medium text-muted-foreground/40 font-mono">{{ run.run_id.slice(0, 8) }}</span>
                </div>
              </div>
            </td>
            <td class="px-3 py-4 align-middle">
              <div class="flex items-center gap-2">
                <div :class="[getStatusToneClass(run.status), 'h-2 w-2 rounded-full']"></div>
                <span class="text-[11px] font-bold text-foreground/70">{{ getStatusLabel(run.status).toUpperCase() }}</span>
              </div>
            </td>
            <td class="px-3 py-4 align-middle">
              <div class="flex flex-wrap gap-1.5">
                <span class="inline-flex items-center gap-1.5 bg-muted/40 px-1.5 py-0.5 rounded text-[10px] font-bold text-muted-foreground/60">
                  <SiteIcon
                    v-if="run.site"
                    :icon-url="getSiteIconUrl(run)"
                    :label="getSiteLabel(run.site)"
                    size="xs"
                  />
                  <span>{{ getSiteLabel(run.site) }}</span>
                </span>
                <span class="bg-muted/40 px-1.5 py-0.5 rounded text-[10px] font-bold text-muted-foreground/60">{{ getModeLabel(run.sync_mode) }}</span>
              </div>
            </td>
            <td class="px-3 py-4 align-middle">
              <div class="flex flex-col gap-0.5">
                <span class="text-[11px] font-semibold text-foreground/60 tabular-nums tracking-tight">{{ getRunTime(run) }}</span>
                <span class="text-[10px] font-medium text-muted-foreground/30">{{ formatDurationMs(run.duration_ms) }} 耗时</span>
              </div>
            </td>
            <td class="px-3 py-4 align-middle">
              <span class="text-[11px] font-medium text-muted-foreground/60">{{ formatRunVideoSummary(run) }}</span>
            </td>
            <td class="px-3 py-4 align-middle pr-6">
              <div class="flex items-center justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                <Button variant="ghost" size="xs" class="h-7 w-7 p-0 rounded-lg hover:bg-background hover:shadow-sm" @click.stop="emit('open-run', run.run_id)">
                  <ChevronRight class="h-4 w-4 text-muted-foreground/40" />
                </Button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-end gap-6 border-t border-border/20 py-6 px-4">
      <span class="text-[11px] font-bold text-muted-foreground/20 uppercase tracking-[0.1em]">第 {{ page }} / {{ totalPages }} 页</span>
      <div class="flex items-center gap-1.5">
        <Button variant="ghost" size="xs" class="h-8 px-4 text-[11px] font-bold rounded-lg border border-border/40" :disabled="page <= 1" @click="emit('change-page', page - 1)">上一页</Button>
        <Button variant="ghost" size="xs" class="h-8 px-4 text-[11px] font-bold rounded-lg border border-border/40" :disabled="page >= totalPages" @click="emit('change-page', page + 1)">下一页</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SyncBoardEmpty from '@/components/sync-center/SyncBoardEmpty.vue'
import SyncBoardSkeleton from '@/components/sync-center/SyncBoardSkeleton.vue'
import SyncSubscriptionSelect from '@/components/sync-center/SyncSubscriptionSelect.vue'

import type { SyncHistoryFilters, SyncRunItem } from '@/composables/useSyncHistory'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDurationMs } from '@/utils/dateFormat'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fromDateToLocal, toCalendarDate } from '@internationalized/date'
import { Calendar as CalendarIcon, Search, ChevronRight } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  embedded?: boolean
  error: string
  filters: Record<string, string>
  loading: boolean
  page: number
  pageSize: number
  runs: SyncRunItem[]
  selectedRunId?: string
  siteOptions: Array<{ value: string; label: string; iconUrl?: string | null }>
  subscriptionOptions: Array<{ value: string; label: string; avatar: string | null }>
  total: number
}>(), {
  embedded: false,
  selectedRunId: '',
})

const emit = defineEmits<{
  (e: 'apply-filters', payload: SyncHistoryFilters): void
  (e: 'change-page', page: number): void
  (e: 'open-run', runId: string): void
}>()

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const siteOptionMap = computed(() => {
  return new Map(props.siteOptions.map((option) => [option.value, option]))
})

const normalizeFilters = (filters: Record<string, string>): SyncHistoryFilters => ({
  status: filters.status || '',
  site: filters.site || '',
  subscriptionId: filters.subscriptionId || '',
  mode: filters.mode || '',
  trigger: filters.trigger || '',
  dateFrom: filters.dateFrom || '',
  dateTo: filters.dateTo || '',
})

const draftFilters = reactive<SyncHistoryFilters>(normalizeFilters(props.filters))

const getAvatarKey = (run: SyncRunItem) => `run-history-${run.run_id}`
const getSiteLabel = (site: string | null) => siteOptionMap.value.get(site || '')?.label || site || 'unknown'
const getSiteIconUrl = (run: SyncRunItem) => run.site_icon_url || siteOptionMap.value.get(run.site || '')?.iconUrl || null

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'running', label: '运行中' },
  { value: 'queued', label: '排队中' },
]

const toDateValue = (isoString: string) => {
  if (!isoString) return undefined
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return undefined
  return toCalendarDate(fromDateToLocal(date))
}

const dateRange = ref<any>({
  start: toDateValue(draftFilters.dateFrom),
  end: toDateValue(draftFilters.dateTo),
})

watch(
  () => props.filters,
  (nextFilters) => {
    Object.assign(draftFilters, normalizeFilters(nextFilters))
    dateRange.value = {
      start: toDateValue(nextFilters.dateFrom || ''),
      end: toDateValue(nextFilters.dateTo || ''),
    }
  },
  { deep: true, immediate: true },
)

const formatDateValue = (value: any) => {
  if (!value) return ''
  return `${value.year}-${String(value.month).padStart(2, '0')}-${String(value.day).padStart(2, '0')}`
}

const dateRangeLabel = computed(() => {
  const start = dateRange.value.start
  const end = dateRange.value.end
  if (!start) return ''
  if (start && end) return `${formatDateValue(start)} - ${formatDateValue(end)}`
  return `${formatDateValue(start)}`
})

const toIsoStartOfDay = (value: any) => {
  if (!value) return ''
  return new Date(value.year, value.month - 1, value.day, 0, 0, 0, 0).toISOString()
}

const toIsoEndOfDay = (value: any) => {
  if (!value) return ''
  return new Date(value.year, value.month - 1, value.day, 23, 59, 59, 999).toISOString()
}

const handleDateRangeUpdate = (nextRange: any) => {
  dateRange.value = nextRange
  if (nextRange?.start) {
    draftFilters.dateFrom = toIsoStartOfDay(nextRange.start)
    draftFilters.dateTo = nextRange.end ? toIsoEndOfDay(nextRange.end) : ''
  } else {
    draftFilters.dateFrom = ''
    draftFilters.dateTo = ''
  }
}

const clearDateRange = () => {
  dateRange.value = { start: undefined, end: undefined }
  draftFilters.dateFrom = ''
  draftFilters.dateTo = ''
}

const updateDraftFilter = (key: keyof SyncHistoryFilters, value: string) => {
  draftFilters[key] = value ?? ''
}

const applyFilters = () => {
  const payload = { ...draftFilters }
  if (dateRange.value.start && !dateRange.value.end) {
    payload.dateTo = toIsoEndOfDay(dateRange.value.start)
  }
  emit('apply-filters', payload)
}

const getStatusToneClass = (status: string) => {
  switch (status) {
    case 'success': return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]'
    case 'failed': return 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]'
    case 'running': return 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.4)]'
    case 'queued': return 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.4)]'
    default: return 'bg-slate-300'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'running': return '运行中'
    case 'queued': return '排队中'
    default: return status || '未知'
  }
}

const getModeLabel = (mode: string) => {
  return mode === 'incremental' ? '增量' : mode === 'full' ? '全量' : mode || '未知'
}

const getRunTime = (run: SyncRunItem) => run.last_event_at || run.finished_at || run.started_at || '—'

const formatRunVideoSummary = (run: SyncRunItem) => {
  if (run.status === 'failed') return '运行失败，查看详情'
  return `已提取 ${run.videos_extracted} 个视频`
}
</script>

<template>
  <div class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border bg-card" :class="embedded ? 'h-full' : ''">
    <div
      class="border-b border-border"
      :class="embedded ? 'px-3 py-2.5' : 'px-4 py-3'"
    >
      <div v-if="embedded" class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-xs font-semibold tracking-[0.14em] text-muted-foreground/70">运行实例</div>
            <div class="mt-1 text-2xs text-muted-foreground">共 {{ total }} 条</div>
          </div>
          <div class="flex items-center gap-2">
            <slot name="header-action" />
            <span class="rounded-full border border-border bg-background px-2 py-0.5 text-2xs text-muted-foreground/70">
              第 {{ page }} / {{ totalPages }} 页
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <div class="w-full sm:w-[9rem]">
            <Select :model-value="filters.status" @update:model-value="(value) => emit('set-filter', { key: 'status', value: String(value ?? '') })">
              <SelectTrigger class="h-8 text-xs">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[9rem]">
            <Select :model-value="filters.site" @update:model-value="(value) => emit('set-filter', { key: 'site', value: String(value ?? '') })">
              <SelectTrigger class="h-8 text-xs">
                <SelectValue placeholder="全部站点" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in siteOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[12rem]">
            <SyncSubscriptionSelect :model-value="filters.subscriptionId" :options="subscriptionOptions" @update:model-value="(value) => emit('set-filter', { key: 'subscriptionId', value: String(value || '') })" />
          </div>

          <div class="w-full sm:w-[9rem]">
            <Select :model-value="filters.mode" @update:model-value="(value) => emit('set-filter', { key: 'mode', value: String(value ?? '') })">
              <SelectTrigger class="h-8 text-xs">
                <SelectValue placeholder="全部模式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in modeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[9rem]">
            <Select :model-value="filters.trigger" @update:model-value="(value) => emit('set-filter', { key: 'trigger', value: String(value ?? '') })">
              <SelectTrigger class="h-8 text-xs">
                <SelectValue placeholder="全部触发" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in triggerOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[14rem] md:w-[16rem]">
            <Popover>
              <PopoverTrigger as-child>
                <Button
                  variant="outline"
                  class="h-8 w-full justify-start overflow-hidden rounded-lg bg-background px-3 text-left text-xs font-normal"
                >
                  <CalendarIcon class="mr-2 h-4 w-4 text-muted-foreground" />
                  <span v-if="dateRangeLabel" class="truncate">{{ dateRangeLabel }}</span>
                  <span v-else class="truncate text-muted-foreground">选择日期范围</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-auto p-0" align="start">
                <div class="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
                  <div class="text-2xs text-muted-foreground">筛选范围</div>
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
        </div>
      </div>

      <div v-else class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-sm font-semibold text-foreground">运行历史</div>
            <div class="mt-1 text-2xs text-muted-foreground">共 {{ total }} 条</div>
          </div>
          <span class="rounded-full border border-border bg-background px-2.5 py-1 text-2xs text-muted-foreground/70">
            第 {{ page }} / {{ totalPages }} 页
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <div class="w-full sm:w-[10rem]">
            <Select :model-value="filters.status" @update:model-value="(value) => emit('set-filter', { key: 'status', value: String(value ?? '') })">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[10rem]">
            <Select :model-value="filters.site" @update:model-value="(value) => emit('set-filter', { key: 'site', value: String(value ?? '') })">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="全部站点" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in siteOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[16rem]">
            <SyncSubscriptionSelect :model-value="filters.subscriptionId" :options="subscriptionOptions" @update:model-value="(value) => emit('set-filter', { key: 'subscriptionId', value: String(value || '') })" />
          </div>

          <div class="w-full sm:w-[10rem]">
            <Select :model-value="filters.mode" @update:model-value="(value) => emit('set-filter', { key: 'mode', value: String(value ?? '') })">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="全部模式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in modeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[10rem]">
            <Select :model-value="filters.trigger" @update:model-value="(value) => emit('set-filter', { key: 'trigger', value: String(value ?? '') })">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="全部触发" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in triggerOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="w-full sm:w-[16rem] md:w-[18rem]">
            <Popover>
              <PopoverTrigger as-child>
                <Button
                  variant="outline"
                  class="h-9 w-full justify-start overflow-hidden rounded-lg bg-background px-3 text-left text-xs font-normal"
                >
                  <CalendarIcon class="mr-2 h-4 w-4 text-muted-foreground" />
                  <span v-if="dateRangeLabel" class="truncate">{{ dateRangeLabel }}</span>
                  <span v-else class="truncate text-muted-foreground">选择日期范围</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-auto p-0" align="start">
                <div class="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
                  <div class="text-2xs text-muted-foreground">筛选范围</div>
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
        </div>
      </div>
    </div>

    <div v-if="error" class="border-b border-border px-3 py-2 text-2xs text-destructive">{{ error }}</div>
    <div v-if="loading" class="flex flex-1 items-center justify-center px-4 py-14 text-sm text-muted-foreground">加载运行历史中...</div>
    <div v-else-if="runs.length === 0" class="flex flex-1 items-center justify-center px-4 py-14 text-sm text-muted-foreground">暂无运行历史</div>

    <div v-else class="flex-1 overflow-auto">
      <table class="w-full min-w-[1180px] text-sm">
        <thead class="sticky top-0 z-10 bg-card">
          <tr class="border-b border-border text-2xs text-muted-foreground/70">
            <th class="px-3 py-2 text-left font-medium">订阅</th>
            <th class="px-3 py-2 text-left font-medium">Run ID</th>
            <th class="px-3 py-2 text-left font-medium">运行状态</th>
            <th class="px-3 py-2 text-left font-medium">模式</th>
            <th class="px-3 py-2 text-left font-medium">站点</th>
            <th class="px-3 py-2 text-left font-medium">触发方式</th>
            <th class="px-3 py-2 text-left font-medium">运行时间</th>
            <th class="px-3 py-2 text-left font-medium">耗时</th>
            <th class="px-3 py-2 text-left font-medium">结果</th>
            <th class="px-3 py-2 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr
            v-for="run in runs"
            :key="run.run_id"
            class="cursor-pointer transition-colors hover:bg-accent"
            :class="selectedRunId === run.run_id ? 'bg-accent' : ''"
            @click="emit('open-run', run.run_id)"
          >
            <td class="px-3 py-2.5 align-middle">
              <div class="flex min-w-0 items-center gap-3">
                <router-link
                  :to="getSubscriptionLink(run.subscription_id)"
                  class="shrink-0"
                  @click.stop
                >
                  <img
                    :src="getAvatarSrc(run.subscription_avatar, getAvatarKey(run))"
                    :alt="run.subscription_name"
                    class="h-7 w-7 rounded-full object-cover bg-background ring-1 ring-border"
                    referrerpolicy="no-referrer"
                    @error="(e) => handleAvatarError(e, getAvatarKey(run))"
                  >
                </router-link>
                <div class="min-w-0">
                  <div class="text-xs font-medium leading-5 text-foreground break-words">{{ run.subscription_name }}</div>
                </div>
              </div>
            </td>
            <td class="px-3 py-2.5 align-middle">
              <div class="max-w-[14rem] break-all font-mono text-2xs text-muted-foreground">{{ run.run_id }}</div>
            </td>
            <td class="px-3 py-2.5 align-middle">
              <Badge :variant="getBadgeVariant(run.status)" class="rounded-full">
                {{ getStatusLabel(run.status) }}
              </Badge>
            </td>
            <td class="px-3 py-2.5 align-middle">
              <span class="rounded-full border border-border bg-background px-2 py-0.5 text-2xs text-muted-foreground/70">{{ getModeLabel(run.sync_mode) }}</span>
            </td>
            <td class="px-3 py-2.5 align-middle text-2xs text-muted-foreground">{{ run.site || 'unknown' }}</td>
            <td class="px-3 py-2.5 align-middle text-2xs text-muted-foreground">{{ getTriggerLabel(run.trigger) }}</td>
            <td class="px-3 py-2.5 align-middle text-2xs text-muted-foreground">{{ getRunTime(run) }}</td>
            <td class="px-3 py-2.5 align-middle text-2xs text-muted-foreground">{{ formatDurationMs(run.duration_ms) }}</td>
            <td class="px-3 py-2.5 align-middle text-2xs text-muted-foreground">{{ formatRunVideoSummary(run) }}</td>
            <td class="px-3 py-2.5 align-middle">
              <div class="flex items-center justify-end gap-2">
                <Button variant="secondary" size="xs" class="rounded-full" @click.stop="emit('open-run', run.run_id)">详情</Button>
                <router-link
                  :to="getSubscriptionLink(run.subscription_id)"
                  class="inline-flex rounded-full border border-border bg-background px-2.5 py-1 text-2xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  @click.stop
                >
                  频道
                </router-link>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-between border-t border-border px-3 py-2.5">
      <span class="text-2xs text-muted-foreground/70">第 {{ page }} / {{ totalPages }} 页</span>
      <div class="flex items-center gap-2">
        <Button variant="secondary" size="xs" class="rounded-full" :disabled="page <= 1" @click="emit('change-page', page - 1)">上一页</Button>
        <Button variant="secondary" size="xs" class="rounded-full" :disabled="page >= totalPages" @click="emit('change-page', page + 1)">下一页</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SyncSubscriptionSelect from '@/components/sync-center/SyncSubscriptionSelect.vue'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDurationMs } from '@/utils/dateFormat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fromDateToLocal, toCalendarDate } from '@internationalized/date'
import { Calendar as CalendarIcon } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  embedded?: boolean
  error: string
  filters: Record<string, string>
  loading: boolean
  page: number
  pageSize: number
  runs: SyncRunItem[]
  selectedRunId?: string
  siteOptions: Array<{ value: string; label: string }>
  subscriptionOptions: Array<{ value: string; label: string; avatar: string | null }>
  total: number
}>(), {
  embedded: false,
  selectedRunId: '',
})

const emit = defineEmits<{
  (e: 'change-page', page: number): void
  (e: 'open-run', runId: string): void
  (e: 'set-filter', payload: { key: string; value: string }): void
}>()

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const getSubscriptionLink = (subscriptionId: number) => `/subscription/${subscriptionId}/all`

const getAvatarKey = (run: SyncRunItem) => `run-history-${run.run_id}`

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'created', label: '已创建' },
  { value: 'queued', label: '排队中' },
  { value: 'running', label: '运行中' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'deferred', label: '已延后' },
  { value: 'timeout', label: '超时' },
]

const modeOptions = [
  { value: '', label: '全部模式' },
  { value: 'incremental', label: '增量' },
  { value: 'full', label: '全量' },
]

const triggerOptions = [
  { value: '', label: '全部触发' },
  { value: 'manual', label: '手动' },
  { value: 'scheduled', label: '调度' },
  { value: 'api', label: '接口' },
]

const toDateValue = (isoString: string) => {
  if (!isoString) {
    return undefined
  }
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) {
    return undefined
  }
  return toCalendarDate(fromDateToLocal(date))
}

const dateRange = ref<any>({
  start: toDateValue(props.filters.dateFrom),
  end: toDateValue(props.filters.dateTo),
})

watch(() => [props.filters.dateFrom, props.filters.dateTo], ([nextFrom, nextTo]) => {
  dateRange.value = {
    start: toDateValue(nextFrom || ''),
    end: toDateValue(nextTo || ''),
  }
})

const formatDateValue = (value: any) => {
  if (!value) {
    return ''
  }
  const year = String(value.year).padStart(4, '0')
  const month = String(value.month).padStart(2, '0')
  const day = String(value.day).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const dateRangeLabel = computed(() => {
  const start = dateRange.value.start
  const end = dateRange.value.end
  if (!start && !end) {
    return ''
  }
  if (start && end) {
    return `${formatDateValue(start)} ~ ${formatDateValue(end)}`
  }
  if (start) {
    return `${formatDateValue(start)} ~ ${formatDateValue(start)}`
  }
  return `${formatDateValue(end)} ~ ${formatDateValue(end)}`
})

const toIsoStartOfDay = (value: any) => {
  if (!value) {
    return ''
  }
  return new Date(value.year, value.month - 1, value.day, 0, 0, 0, 0).toISOString()
}

const toIsoEndOfDay = (value: any) => {
  if (!value) {
    return ''
  }
  return new Date(value.year, value.month - 1, value.day, 23, 59, 59, 999).toISOString()
}

const emitDateRange = (range: any) => {
  const start = range.start
  const end = range.end || range.start
  if (!start && !end) {
    emit('set-filter', { key: 'dateFrom', value: '' })
    emit('set-filter', { key: 'dateTo', value: '' })
    return
  }
  emit('set-filter', { key: 'dateFrom', value: toIsoStartOfDay(start) })
  emit('set-filter', { key: 'dateTo', value: toIsoEndOfDay(end) })
}

const handleDateRangeUpdate = (nextRange: any) => {
  dateRange.value = nextRange
  emitDateRange(nextRange)
}

const clearDateRange = () => {
  const cleared = { start: undefined, end: undefined }
  dateRange.value = cleared
  emitDateRange(cleared)
}

const getBadgeVariant = (status: string) => {
  switch (status) {
    case 'success':
      return 'secondary'
    case 'failed':
      return 'destructive'
    case 'deferred':
    case 'timeout':
      return 'outline'
    case 'queued':
    case 'running':
      return 'default'
    default:
      return 'outline'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'created':
      return '已创建'
    case 'queued':
      return '排队中'
    case 'running':
      return '运行中'
    case 'success':
      return '成功'
    case 'failed':
      return '失败'
    case 'deferred':
      return '已延后'
    case 'timeout':
      return '超时'
    default:
      return status || '未知'
  }
}

const getModeLabel = (mode: string) => {
  return mode === 'incremental' ? '增量' : mode === 'full' ? '全量' : mode || '未知'
}

const getTriggerLabel = (trigger: string | null) => {
  switch (trigger) {
    case 'manual':
      return '手动'
    case 'scheduled':
      return '调度'
    case 'api':
      return '接口'
    default:
      return trigger || '未知'
  }
}

const getRunTime = (run: SyncRunItem) => run.last_event_at || run.finished_at || run.started_at || '—'

const formatRunVideoSummary = (run: SyncRunItem) => {
  if (run.status === 'failed') {
    return '点击查看详情'
  }
  const foundLabel = run.sync_mode === 'incremental' ? '新增' : '发现'
  return `${foundLabel} ${run.videos_found} · 提取 ${run.videos_extracted}`
}
</script>

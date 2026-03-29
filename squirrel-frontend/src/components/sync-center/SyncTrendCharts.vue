<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <div class="pb-4">
      <div class="flex items-center justify-between gap-3 px-1">
        <div class="space-y-0.5">
          <h2 class="text-sm font-medium text-foreground">趋势切片</h2>
          <p class="text-xs text-muted-foreground/70">范围 {{ range.toUpperCase() }} · {{ series.length }} 时间桶</p>
        </div>
        <div class="flex items-center gap-2">
          <Select :model-value="range" @update:model-value="(value) => emit('set-range', String(value ?? '24h'))">
            <SelectTrigger class="h-7 w-20 border-none bg-muted/50 text-[11px] focus:ring-0">
              <SelectValue :placeholder="range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="option in rangeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>

    <div v-if="error" class="px-1 py-3 text-xs text-destructive/80">{{ error }}</div>
    <div v-if="loading" class="flex flex-1 items-center justify-center py-12 text-xs text-muted-foreground/60">同步数据演进中...</div>
    <div v-else-if="series.length === 0" class="flex flex-1 items-center justify-center py-12 text-xs text-muted-foreground/60">暂无趋势记录</div>

    <div v-else class="flex-1 min-h-0 grid grid-cols-1 gap-6" :class="embedded ? '' : 'xl:grid-cols-[1.5fr_1fr]'">
      <div class="flex min-h-0 flex-col overflow-hidden">
        <div class="text-[10px] uppercase tracking-wider text-muted-foreground/40 mb-3 px-1">时间序列历史</div>
        <div class="flex-1 overflow-auto rounded-lg border border-border/40 bg-muted/20">
          <table class="w-full text-[11px]">
            <thead>
              <tr class="text-left text-muted-foreground/50 border-b border-border/40">
                <th class="px-3 py-2 font-medium">时间桶</th>
                <th class="px-3 py-2 font-medium">运行数</th>
                <th class="px-3 py-2 font-medium">成功</th>
                <th class="px-3 py-2 font-medium">失败</th>
                <th class="px-3 py-2 font-medium">提取数</th>
                <th class="px-3 py-2 font-medium">P95 耗时</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/20">
              <tr v-for="point in displaySeries" :key="`${point.bucket_time}-${point.site}-${point.sync_mode}-${point.trigger}`" class="text-muted-foreground/70 transition-colors hover:bg-muted/30">
                <td class="px-3 py-2 text-foreground/80 font-medium">{{ point.bucket_time }}</td>
                <td class="px-3 py-2 tabular-nums">{{ point.runs_total }}</td>
                <td class="px-3 py-2 tabular-nums text-emerald-600/70">{{ point.runs_success }}</td>
                <td class="px-3 py-2 tabular-nums" :class="point.runs_failed > 0 ? 'text-rose-600/70' : ''">{{ point.runs_failed }}</td>
                <td class="px-3 py-2 tabular-nums text-blue-600/70">{{ point.videos_extracted }}</td>
                <td class="px-3 py-2 tabular-nums">{{ formatDurationMs(point.p95_duration_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="flex min-h-0 flex-col overflow-hidden">
        <div class="text-[10px] uppercase tracking-wider text-muted-foreground/40 mb-3 px-1">站点分布</div>
        <div class="flex-1 overflow-auto rounded-lg border border-border/40 bg-muted/20">
          <table class="w-full text-[11px]">
            <thead>
              <tr class="text-left text-muted-foreground/50 border-b border-border/40">
                <th class="px-3 py-2 font-medium">站点</th>
                <th class="px-3 py-2 font-medium">运行数</th>
                <th class="px-3 py-2 font-medium">成功</th>
                <th class="px-3 py-2 font-medium">失败</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/20">
              <tr v-for="item in displaySites" :key="item.site" class="text-muted-foreground/70 transition-colors hover:bg-muted/30">
                <td class="px-3 py-2 text-foreground/80 font-medium">{{ item.site }}</td>
                <td class="px-3 py-2 tabular-nums">{{ item.runs_total }}</td>
                <td class="px-3 py-2 tabular-nums">{{ item.runs_success }}</td>
                <td class="px-3 py-2 tabular-nums" :class="item.runs_failed > 0 ? 'text-rose-600/70' : ''">{{ item.runs_failed }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SyncTrendPoint, SyncTrendSiteBreakdown } from '@/composables/useSyncTrends'
import { formatDurationMs } from '@/utils/dateFormat'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const props = withDefaults(defineProps<{
  embedded?: boolean
  error: string
  filters: Record<string, string>
  loading: boolean
  range: string
  series: SyncTrendPoint[]
  siteBreakdown: SyncTrendSiteBreakdown[]
}>(), {
  embedded: false,
})

const emit = defineEmits<{
  (e: 'set-filter', payload: { key: string; value: string }): void
  (e: 'set-range', value: string): void
}>()

const rangeOptions = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
]

const displaySeries = computed(() => {
  if (!props.embedded) {
    return props.series
  }
  return props.series.slice(-12).reverse()
})

const displaySites = computed(() => {
  if (!props.embedded) {
    return props.siteBreakdown
  }
  return props.siteBreakdown.slice(0, 12)
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-border bg-card">
    <div class="border-b border-border px-3 py-2.5">
      <div class="flex items-center justify-between gap-3">
        <div>
          <div class="text-xs font-semibold tracking-[0.14em] text-muted-foreground/70">趋势切片</div>
          <div class="mt-1 text-2xs text-muted-foreground">范围 {{ range.toUpperCase() }} · 时间桶 {{ series.length }}</div>
        </div>
        <span class="rounded-full border border-border bg-background px-2 py-0.5 text-2xs text-muted-foreground/70">
          站点 {{ siteBreakdown.length }}
        </span>
      </div>

      <div v-if="!embedded" class="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-[1.1fr_1fr_1fr_1fr]">
        <Select :model-value="range" @update:model-value="(value) => emit('set-range', String(value ?? '24h'))">
          <SelectTrigger class="h-9 text-xs">
            <SelectValue placeholder="24h" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="option in rangeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </SelectItem>
          </SelectContent>
        </Select>
        <input :value="filters.site" type="text" placeholder="站点" class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground" @input="emitInput('site', $event)" />
        <input :value="filters.mode" type="text" placeholder="模式" class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground" @input="emitInput('mode', $event)" />
        <input :value="filters.trigger" type="text" placeholder="触发方式" class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground" @input="emitInput('trigger', $event)" />
      </div>
    </div>

    <div v-if="error" class="border-b border-border px-3 py-2 text-2xs text-destructive">{{ error }}</div>
    <div v-if="loading" class="px-4 py-12 text-center text-sm text-muted-foreground">加载趋势数据中...</div>
    <div v-else-if="series.length === 0" class="px-4 py-12 text-center text-sm text-muted-foreground">当前条件下没有趋势数据</div>

    <div v-else class="flex-1 min-h-0 grid grid-cols-1 gap-3 p-3" :class="embedded ? '' : 'xl:grid-cols-[1.3fr_1fr]'">
      <div class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-background">
        <div class="border-b border-border px-3 py-2 text-2xs font-semibold tracking-[0.12em] text-muted-foreground/70">时间序列</div>
        <div class="flex-1 overflow-auto">
          <table class="w-full" :class="embedded ? 'min-w-[460px]' : 'min-w-[560px]'">
            <thead class="border-b border-border">
              <tr class="text-left text-2xs text-muted-foreground/70">
                <th class="px-3 py-2 font-semibold">时间桶</th>
                <th class="px-3 py-2 font-semibold">运行</th>
                <th class="px-3 py-2 font-semibold">成功</th>
                <th class="px-3 py-2 font-semibold">失败</th>
                <th class="px-3 py-2 font-semibold">提取</th>
                <th class="px-3 py-2 font-semibold">P95</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr v-for="point in displaySeries" :key="`${point.bucket_time}-${point.site}-${point.sync_mode}-${point.trigger}`" class="text-2xs text-muted-foreground">
                <td class="px-3 py-2 text-foreground">{{ point.bucket_time }}</td>
                <td class="px-3 py-2">{{ point.runs_total }}</td>
                <td class="px-3 py-2">{{ point.runs_success }}</td>
                <td class="px-3 py-2">{{ point.runs_failed }}</td>
                <td class="px-3 py-2">{{ point.videos_extracted }}</td>
                <td class="px-3 py-2">{{ formatDurationMs(point.p95_duration_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-background">
        <div class="border-b border-border px-3 py-2 text-2xs font-semibold tracking-[0.12em] text-muted-foreground/70">站点分布</div>
        <div class="flex-1 overflow-auto">
          <table class="w-full" :class="embedded ? 'min-w-[360px]' : 'min-w-[320px]'">
            <thead class="border-b border-border">
              <tr class="text-left text-2xs text-muted-foreground/70">
                <th class="px-3 py-2 font-semibold">站点</th>
                <th class="px-3 py-2 font-semibold">运行</th>
                <th class="px-3 py-2 font-semibold">成功</th>
                <th class="px-3 py-2 font-semibold">失败</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr v-for="item in displaySites" :key="item.site" class="text-2xs text-muted-foreground">
                <td class="px-3 py-2 text-foreground">{{ item.site }}</td>
                <td class="px-3 py-2">{{ item.runs_total }}</td>
                <td class="px-3 py-2">{{ item.runs_success }}</td>
                <td class="px-3 py-2">{{ item.runs_failed }}</td>
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
  return props.series.slice(-8).reverse()
})

const displaySites = computed(() => {
  if (!props.embedded) {
    return props.siteBreakdown
  }
  return props.siteBreakdown.slice(0, 8)
})

const emitInput = (key: string, event: Event) => {
  const target = event.target as HTMLInputElement | null
  emit('set-filter', { key, value: target?.value || '' })
}
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-3">
      <Card class="p-4">
        <p class="text-2xs text-text-tertiary">总运行数</p>
        <p class="text-2xl font-semibold text-text-primary mt-2">{{ totalRuns }}</p>
      </Card>
      <Card class="p-4">
        <p class="text-2xs text-text-tertiary">成功</p>
        <p class="text-2xl font-semibold text-color-success mt-2">{{ totalSuccess }}</p>
      </Card>
      <Card class="p-4">
        <p class="text-2xs text-text-tertiary">失败</p>
        <p class="text-2xl font-semibold text-color-error mt-2">{{ totalFailed }}</p>
      </Card>
      <Card class="p-4">
        <p class="text-2xs text-text-tertiary">P95 时延</p>
        <p class="text-2xl font-semibold text-text-primary mt-2">{{ latestP95 }} ms</p>
      </Card>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1.2fr_1fr_1fr_1fr] gap-3">
      <Select size="sm" :model-value="range" :options="rangeOptions" @update:model-value="(value) => emit('set-range', String(value || '24h'))" />
      <input :value="filters.site" type="text" placeholder="站点" class="w-full px-3 py-2 text-sm rounded-lg bg-bg-secondary border border-border-primary text-text-primary" @input="emitInput('site', $event)" />
      <input :value="filters.mode" type="text" placeholder="模式" class="w-full px-3 py-2 text-sm rounded-lg bg-bg-secondary border border-border-primary text-text-primary" @input="emitInput('mode', $event)" />
      <input :value="filters.trigger" type="text" placeholder="触发方式" class="w-full px-3 py-2 text-sm rounded-lg bg-bg-secondary border border-border-primary text-text-primary" @input="emitInput('trigger', $event)" />
    </div>

    <div v-if="error" class="text-xs text-color-error">{{ error }}</div>
    <div v-if="loading" class="text-sm text-text-muted">加载趋势数据中...</div>

    <div v-else class="grid grid-cols-1 xl:grid-cols-[1.3fr_1fr] gap-4">
      <Card class="p-4 overflow-x-auto">
        <h3 class="text-sm font-medium text-text-primary mb-3">时间序列</h3>
        <table class="w-full min-w-[760px]">
          <thead>
            <tr class="text-left text-2xs text-text-tertiary border-b border-border-primary">
              <th class="py-2 pr-3">时间桶</th>
              <th class="py-2 pr-3">运行</th>
              <th class="py-2 pr-3">成功</th>
              <th class="py-2 pr-3">失败</th>
              <th class="py-2 pr-3">发现</th>
              <th class="py-2 pr-3">入队</th>
              <th class="py-2 pr-3">提取</th>
              <th class="py-2 pr-3">P95</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-primary">
            <tr v-for="point in series" :key="`${point.bucket_time}-${point.site}-${point.sync_mode}-${point.trigger}`" class="text-xs text-text-secondary">
              <td class="py-2 pr-3">{{ point.bucket_time }}</td>
              <td class="py-2 pr-3">{{ point.runs_total }}</td>
              <td class="py-2 pr-3">{{ point.runs_success }}</td>
              <td class="py-2 pr-3">{{ point.runs_failed }}</td>
              <td class="py-2 pr-3">{{ point.videos_found }}</td>
              <td class="py-2 pr-3">{{ point.videos_enqueued }}</td>
              <td class="py-2 pr-3">{{ point.videos_extracted }}</td>
              <td class="py-2 pr-3">{{ point.p95_duration_ms }}</td>
            </tr>
          </tbody>
        </table>
      </Card>

      <Card class="p-4 overflow-x-auto">
        <h3 class="text-sm font-medium text-text-primary mb-3">站点分布</h3>
        <table class="w-full min-w-[320px]">
          <thead>
            <tr class="text-left text-2xs text-text-tertiary border-b border-border-primary">
              <th class="py-2 pr-3">站点</th>
              <th class="py-2 pr-3">运行</th>
              <th class="py-2 pr-3">成功</th>
              <th class="py-2 pr-3">失败</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-primary">
            <tr v-for="item in siteBreakdown" :key="item.site" class="text-xs text-text-secondary">
              <td class="py-2 pr-3">{{ item.site }}</td>
              <td class="py-2 pr-3">{{ item.runs_total }}</td>
              <td class="py-2 pr-3">{{ item.runs_success }}</td>
              <td class="py-2 pr-3">{{ item.runs_failed }}</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, Select } from '@/components/common'
import type { SyncTrendPoint, SyncTrendSiteBreakdown } from '@/composables/useSyncTrends'

const props = defineProps<{
  error: string
  filters: Record<string, string>
  loading: boolean
  range: string
  series: SyncTrendPoint[]
  siteBreakdown: SyncTrendSiteBreakdown[]
}>()

const emit = defineEmits<{
  (e: 'set-filter', key: string, value: string): void
  (e: 'set-range', value: string): void
}>()

const rangeOptions = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
]

const totalRuns = computed(() => props.series.reduce((sum, point) => sum + point.runs_total, 0))
const totalSuccess = computed(() => props.series.reduce((sum, point) => sum + point.runs_success, 0))
const totalFailed = computed(() => props.series.reduce((sum, point) => sum + point.runs_failed, 0))
const latestP95 = computed(() => {
  if (!props.series.length) {
    return 0
  }
  return props.series[props.series.length - 1]?.p95_duration_ms || 0
})

const emitInput = (key: string, event: Event) => {
  const target = event.target as HTMLInputElement | null
  emit('set-filter', key, target?.value || '')
}
</script>

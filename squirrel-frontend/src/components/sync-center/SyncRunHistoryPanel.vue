<template>
  <div class="bg-bg-secondary border border-border-primary rounded-2xl overflow-hidden h-full flex flex-col min-h-0">
    <div class="px-4 py-3 border-b border-border-primary grid grid-cols-1 lg:grid-cols-6 gap-3">
      <Select size="sm" :model-value="filters.status" :options="statusOptions" @update:model-value="(value) => emit('set-filter', 'status', String(value || ''))" />
      <input :value="filters.site" type="text" placeholder="站点" class="w-full px-3 py-2 text-sm rounded-lg bg-bg-primary border border-border-primary text-text-primary" @input="emitInput('site', $event)" />
      <Select size="sm" :model-value="filters.mode" :options="modeOptions" @update:model-value="(value) => emit('set-filter', 'mode', String(value || ''))" />
      <Select size="sm" :model-value="filters.trigger" :options="triggerOptions" @update:model-value="(value) => emit('set-filter', 'trigger', String(value || ''))" />
      <input :value="filters.dateFrom" type="datetime-local" class="w-full px-3 py-2 text-sm rounded-lg bg-bg-primary border border-border-primary text-text-primary" @input="emitInput('dateFrom', $event)" />
      <input :value="filters.dateTo" type="datetime-local" class="w-full px-3 py-2 text-sm rounded-lg bg-bg-primary border border-border-primary text-text-primary" @input="emitInput('dateTo', $event)" />
    </div>

    <div v-if="error" class="px-4 py-3 text-xs text-color-error border-b border-border-primary">{{ error }}</div>

    <div v-if="loading" class="flex-1 flex items-center justify-center text-sm text-text-muted">加载运行历史中...</div>
    <div v-else-if="runs.length === 0" class="flex-1 flex items-center justify-center text-sm text-text-muted">暂无运行历史</div>
    <div v-else class="flex-1 overflow-y-auto">
      <div class="divide-y divide-border-primary">
        <button
          v-for="run in runs"
          :key="run.run_id"
          type="button"
          class="w-full text-left px-4 py-4 hover:bg-bg-hover transition-colors"
          @click="emit('open-run', run.run_id)"
        >
          <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-text-primary truncate">{{ run.subscription_name }}</span>
                <StatusBadge size="xs" :show-dot="false" :variant="getVariant(run.status)" :label="run.status" class="border-0" />
                <span class="px-2 py-0.5 rounded-full text-2xs bg-bg-primary text-text-tertiary border border-border-primary">{{ run.sync_mode }}</span>
              </div>
              <div class="text-2xs text-text-muted mt-1">
                {{ run.site || 'unknown' }} · {{ run.trigger || 'unknown' }} · {{ run.last_event_at }}
              </div>
            </div>
            <div class="text-right text-2xs text-text-secondary">
              <div>耗时 {{ run.duration_ms }} ms</div>
              <div class="mt-1">发现 {{ run.videos_found }} · 入队 {{ run.videos_enqueued }} · 提取 {{ run.videos_extracted }}</div>
            </div>
          </div>
          <div v-if="run.error_message" class="text-2xs text-color-error mt-2 truncate">{{ run.error_message }}</div>
        </button>
      </div>
    </div>

    <div v-if="totalPages > 1" class="px-4 py-3 border-t border-border-primary flex items-center justify-between">
      <span class="text-2xs text-text-tertiary">第 {{ page }} / {{ totalPages }} 页</span>
      <div class="flex items-center gap-2">
        <Button size="xs" shape="pill" variant="secondary" :disabled="page <= 1" @click="emit('change-page', page - 1)">上一页</Button>
        <Button size="xs" shape="pill" variant="secondary" :disabled="page >= totalPages" @click="emit('change-page', page + 1)">下一页</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Select, StatusBadge } from '@/components/common'
import type { SyncRunItem } from '@/composables/useSyncHistory'

const props = defineProps<{
  error: string
  filters: Record<string, string>
  loading: boolean
  page: number
  pageSize: number
  runs: SyncRunItem[]
  total: number
}>()

const emit = defineEmits<{
  (e: 'change-page', page: number): void
  (e: 'open-run', runId: string): void
  (e: 'set-filter', key: string, value: string): void
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'created', label: 'created' },
  { value: 'queued', label: 'queued' },
  { value: 'running', label: 'running' },
  { value: 'success', label: 'success' },
  { value: 'failed', label: 'failed' },
  { value: 'deferred', label: 'deferred' },
  { value: 'timeout', label: 'timeout' },
]

const modeOptions = [
  { value: '', label: '全部模式' },
  { value: 'incremental', label: 'incremental' },
  { value: 'full', label: 'full' },
]

const triggerOptions = [
  { value: '', label: '全部触发' },
  { value: 'manual', label: 'manual' },
  { value: 'scheduled', label: 'scheduled' },
  { value: 'api', label: 'api' },
]

const emitInput = (key: string, event: Event) => {
  const target = event.target as HTMLInputElement | null
  emit('set-filter', key, target?.value || '')
}

const getVariant = (status: string) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'error'
    case 'deferred':
      return 'warning'
    case 'queued':
    case 'running':
      return 'info'
    default:
      return 'default'
  }
}
</script>

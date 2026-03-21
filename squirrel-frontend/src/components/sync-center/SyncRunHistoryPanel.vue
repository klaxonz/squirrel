<template>
  <div class="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border-primary bg-bg-secondary">
    <div
      class="border-b border-border-primary"
      :class="embedded ? 'px-3 py-2.5' : 'px-4 py-3'"
    >
      <div v-if="embedded" class="flex items-center justify-between gap-3">
        <div>
          <div class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">运行实例</div>
          <div class="mt-1 text-2xs text-text-muted">共 {{ total }} 条</div>
        </div>
        <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
          第 {{ page }} / {{ totalPages }} 页
        </span>
      </div>

      <div v-else class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-sm font-semibold text-text-primary">运行历史</div>
            <div class="mt-1 text-2xs text-text-muted">共 {{ total }} 条</div>
          </div>
          <span class="rounded-full border border-border-primary bg-bg-primary px-2.5 py-1 text-2xs text-text-tertiary">
            第 {{ page }} / {{ totalPages }} 页
          </span>
        </div>

        <div class="grid grid-cols-1 gap-3 lg:grid-cols-6">
          <Select size="sm" :model-value="filters.status" :options="statusOptions" @update:model-value="(value) => emit('set-filter', { key: 'status', value: String(value || '') })" />
          <input :value="filters.site" type="text" placeholder="站点" class="w-full rounded-lg border border-border-primary bg-bg-primary px-3 py-2 text-sm text-text-primary" @input="emitInput('site', $event)" />
          <Select size="sm" :model-value="filters.mode" :options="modeOptions" @update:model-value="(value) => emit('set-filter', { key: 'mode', value: String(value || '') })" />
          <Select size="sm" :model-value="filters.trigger" :options="triggerOptions" @update:model-value="(value) => emit('set-filter', { key: 'trigger', value: String(value || '') })" />
          <input :value="filters.dateFrom" type="datetime-local" class="w-full rounded-lg border border-border-primary bg-bg-primary px-3 py-2 text-sm text-text-primary" @input="emitInput('dateFrom', $event)" />
          <input :value="filters.dateTo" type="datetime-local" class="w-full rounded-lg border border-border-primary bg-bg-primary px-3 py-2 text-sm text-text-primary" @input="emitInput('dateTo', $event)" />
        </div>
      </div>
    </div>

    <div v-if="error" class="border-b border-border-primary px-3 py-2 text-2xs text-color-error">{{ error }}</div>
    <div v-if="loading" class="flex flex-1 items-center justify-center px-4 py-14 text-sm text-text-muted">加载运行历史中...</div>
    <div v-else-if="runs.length === 0" class="flex flex-1 items-center justify-center px-4 py-14 text-sm text-text-muted">暂无运行历史</div>

    <div v-else class="flex-1 overflow-y-auto">
      <div class="divide-y divide-border-primary">
        <button
          v-for="run in runs"
          :key="run.run_id"
          type="button"
          class="w-full text-left transition-colors hover:bg-bg-hover"
          :class="[embedded ? 'px-3 py-2.5' : 'px-4 py-3', selectedRunId === run.run_id ? 'bg-bg-hover' : '']"
          @click="emit('open-run', run.run_id)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="truncate text-xs font-medium text-text-primary">{{ run.subscription_name }}</span>
                <StatusBadge size="xs" :show-dot="false" :variant="getVariant(run.status)" :label="getStatusLabel(run.status)" class="border-0" />
                <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">{{ getModeLabel(run.sync_mode) }}</span>
              </div>
              <div class="mt-1 truncate text-2xs text-text-tertiary">
                {{ run.site || 'unknown' }} · {{ getTriggerLabel(run.trigger) }} · {{ run.last_event_at || run.finished_at || run.started_at || '—' }}
              </div>
              <div v-if="run.error_message" class="mt-1 truncate text-2xs text-color-error">{{ run.error_message }}</div>
            </div>
            <div class="shrink-0 text-right text-2xs text-text-secondary">
              <div>{{ run.duration_ms }} ms</div>
              <div class="mt-1">{{ formatRunVideoSummary(run) }}</div>
            </div>
          </div>
        </button>
      </div>
    </div>

    <div v-if="totalPages > 1" class="flex items-center justify-between border-t border-border-primary px-3 py-2.5">
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

const props = withDefaults(defineProps<{
  embedded?: boolean
  error: string
  filters: Record<string, string>
  loading: boolean
  page: number
  pageSize: number
  runs: SyncRunItem[]
  selectedRunId?: string
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

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

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

const emitInput = (key: string, event: Event) => {
  const target = event.target as HTMLInputElement | null
  emit('set-filter', { key, value: target?.value || '' })
}

const getVariant = (status: string) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'error'
    case 'deferred':
    case 'timeout':
      return 'warning'
    case 'queued':
    case 'running':
      return 'info'
    default:
      return 'default'
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

const formatRunVideoSummary = (run: SyncRunItem) => {
  const foundLabel = run.sync_mode === 'incremental' ? '新增' : '发现'
  return `${foundLabel} ${run.videos_found} · 提取 ${run.videos_extracted}`
}
</script>

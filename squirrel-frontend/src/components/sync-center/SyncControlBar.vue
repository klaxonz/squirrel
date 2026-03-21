<template>
  <section class="flex flex-col gap-3 border-b border-border-primary pb-3">
    <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="text-lg font-semibold tracking-tight text-text-primary">同步中心</h1>
          <span class="rounded-full border border-border-primary bg-bg-secondary px-2.5 py-1 text-2xs text-text-tertiary">
            {{ summary }}
          </span>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <div class="inline-flex items-center gap-1 rounded-full border border-border-primary bg-bg-secondary p-1">
          <button
            v-for="option in lensOptions"
            :key="option.value"
            type="button"
            class="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            :class="lens === option.value
              ? 'bg-bg-elevated text-text-primary shadow-sm'
              : 'text-text-muted hover:bg-bg-hover hover:text-text-primary'"
            @click="emit('set-lens', option.value)"
          >
            {{ option.label }}
          </button>
        </div>

        <label class="inline-flex items-center gap-2 rounded-full border border-border-primary bg-bg-secondary px-3 py-1.5 text-xs text-text-secondary">
          <input
            :checked="autoRefresh"
            type="checkbox"
            class="h-3.5 w-3.5 rounded border-border-primary bg-bg-primary"
            @change="handleToggleAutoRefresh"
          >
          自动刷新
        </label>

        <Button
          size="sm"
          shape="pill"
          variant="secondary"
          :loading="refreshing"
          @click="emit('refresh')"
        >
          刷新
        </Button>

        <Button
          size="sm"
          shape="pill"
          variant="primary"
          :disabled="!canRetryFailed"
          :loading="retryingBatch"
          @click="emit('retry-failed')"
        >
          重试失败项
        </Button>

        <Button
          size="sm"
          shape="pill"
          variant="ghost"
          :loading="reconciling"
          @click="emit('reconcile')"
        >
          对账
        </Button>

        <span class="rounded-full border border-border-primary bg-bg-secondary px-3 py-1.5 text-2xs text-text-tertiary">
          更新 {{ lastUpdatedAt || '—' }}
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Button } from '@/components/common'
import type { SyncTimeLens } from '@/composables/useSyncCenterWorkbench'

const props = defineProps<{
  summary: string
  lens: SyncTimeLens
  autoRefresh: boolean
  canRetryFailed: boolean
  refreshing: boolean
  retryingBatch: boolean
  reconciling: boolean
  lastUpdatedAt: string
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'reconcile'): void
  (e: 'retry-failed'): void
  (e: 'set-lens', value: SyncTimeLens): void
  (e: 'toggle-auto-refresh', value: boolean): void
}>()

const lensOptions: Array<{ value: SyncTimeLens; label: string }> = [
  { value: 'now', label: '现在' },
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
]

const handleToggleAutoRefresh = (event: Event) => {
  const target = event.target as HTMLInputElement | null
  emit('toggle-auto-refresh', !!target?.checked)
}
</script>

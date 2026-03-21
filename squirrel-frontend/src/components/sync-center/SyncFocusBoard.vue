<template>
  <section class="grid grid-cols-1 gap-3 xl:grid-cols-2 2xl:grid-cols-4">
    <div
      v-for="section in sections"
      :key="section.key"
      class="overflow-hidden rounded-2xl border bg-bg-secondary"
      :class="activeFocus === section.key ? 'border-border-hover' : 'border-border-primary'"
    >
      <button
        type="button"
        class="flex w-full items-center justify-between border-b border-border-primary px-3 py-2.5 text-left"
        @click="emit('open', { section: section.key })"
      >
        <span class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">{{ section.label }}</span>
        <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
          {{ section.rows.length }}
        </span>
      </button>

      <div v-if="section.rows.length" class="divide-y divide-border-primary">
        <button
          v-for="row in section.rows"
          :key="`${section.key}-${row.id}`"
          type="button"
          class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-bg-hover"
          @click="emit('open', { section: section.key, id: row.id })"
        >
          <div class="min-w-0">
            <div class="truncate text-xs font-medium text-text-primary">{{ row.title }}</div>
            <div class="mt-0.5 truncate text-2xs text-text-tertiary">{{ row.meta }}</div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <span class="h-2 w-2 rounded-full" :class="getDotClass(row.tone)"></span>
            <span class="text-xs font-semibold" :class="getValueClass(row.tone)">{{ row.value }}</span>
          </div>
        </button>
      </div>

      <div v-else class="px-3 py-6 text-center text-2xs text-text-muted">
        当前没有信号
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SyncFocusKind } from '@/composables/useSyncCenterWorkbench'

type FocusTone = 'neutral' | 'info' | 'warning' | 'error' | 'success'
type FocusSectionKey = Extract<SyncFocusKind, 'site' | 'failed-runs' | 'slow-runs' | 'recovery'>

export interface SyncFocusRow {
  id: string
  title: string
  meta: string
  value: string | number
  tone: FocusTone
}

const props = defineProps<{
  activeFocus: SyncFocusKind
  sites: SyncFocusRow[]
  failedRuns: SyncFocusRow[]
  slowRuns: SyncFocusRow[]
  recovery: SyncFocusRow[]
}>()

const emit = defineEmits<{
  (e: 'open', payload: { section: FocusSectionKey; id?: string }): void
}>()

const sections = computed<Array<{ key: FocusSectionKey; label: string; rows: SyncFocusRow[] }>>(() => ([
  { key: 'site', label: '异常站点', rows: props.sites },
  { key: 'failed-runs', label: '失败批次', rows: props.failedRuns },
  { key: 'slow-runs', label: '高延迟批次', rows: props.slowRuns },
  { key: 'recovery', label: '恢复事件', rows: props.recovery },
]))

const getValueClass = (tone: FocusTone) => {
  switch (tone) {
    case 'error':
      return 'text-color-error'
    case 'info':
      return 'text-color-info'
    case 'warning':
      return 'text-color-warning'
    case 'success':
      return 'text-color-success'
    default:
      return 'text-text-primary'
  }
}

const getDotClass = (tone: FocusTone) => {
  switch (tone) {
    case 'error':
      return 'bg-color-error'
    case 'info':
      return 'bg-color-info'
    case 'warning':
      return 'bg-color-warning'
    case 'success':
      return 'bg-color-success'
    default:
      return 'bg-text-muted'
  }
}
</script>

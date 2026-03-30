<template>
  <section class="min-h-0">
    <div class="flex flex-col gap-10">
      <SyncSignalMatrix
        :current="current"
        :recent="recent"
        @select="emit('signal-select', $event)"
      />

      <SyncRunHistoryPanel
        class="min-h-0"
        embedded
        :error="runsError"
        :filters="runFilters"
        :loading="runsLoading"
        :page="runPage"
        :page-size="runPageSize"
        :runs="runs"
        :selected-run-id="selectedRunId"
        :site-options="siteOptions"
        :subscription-options="subscriptionOptions"
        @apply-filters="emit('apply-history-filters', $event)"
        :total="runTotal"
        @change-page="emit('change-history-page', $event)"
        @open-run="emit('open-run', $event)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import SyncRunHistoryPanel from '@/components/sync-center/SyncRunHistoryPanel.vue'
import SyncSignalMatrix, { type SyncSignalItem } from '@/components/sync-center/SyncSignalMatrix.vue'
import type { SyncHistoryFilters, SyncRunItem } from '@/composables/useSyncHistory'

const props = defineProps<{
  current: SyncSignalItem[]
  recent: SyncSignalItem[]
  runs: SyncRunItem[]
  runsError: string
  runsLoading: boolean
  runFilters: Record<string, string>
  runPage: number
  runPageSize: number
  runTotal: number
  siteOptions: Array<{ value: string; label: string; iconUrl?: string | null }>
  subscriptionOptions: Array<{ value: string; label: string; avatar: string | null }>
  selectedRunId: string
}>()

const emit = defineEmits<{
  (e: 'signal-select', key: string): void
  (e: 'apply-history-filters', payload: SyncHistoryFilters): void
  (e: 'change-history-page', page: number): void
  (e: 'open-run', runId: string): void
}>()
</script>

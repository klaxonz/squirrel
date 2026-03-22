<template>
  <section class="min-h-0 xl:h-[min(44rem,calc(var(--app-content-height)-18rem))]">
    <SyncRunHistoryPanel
      class="min-h-0 h-full"
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
      :total="runTotal"
      @change-page="emit('change-history-page', $event)"
      @open-run="emit('open-run', $event)"
      @set-filter="emit('change-history-filter', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import SyncRunHistoryPanel from '@/components/sync-center/SyncRunHistoryPanel.vue'
import type { SyncRunItem } from '@/composables/useSyncHistory'

const props = defineProps<{
  runs: SyncRunItem[]
  runsError: string
  runsLoading: boolean
  runFilters: Record<string, string>
  runPage: number
  runPageSize: number
  runTotal: number
  siteOptions: Array<{ value: string; label: string }>
  subscriptionOptions: Array<{ value: string; label: string; avatar: string | null }>
  selectedRunId: string
}>()

const emit = defineEmits<{
  (e: 'change-history-filter', payload: { key: string; value: string }): void
  (e: 'change-history-page', page: number): void
  (e: 'open-run', runId: string): void
}>()
</script>

<template>
  <div class="grid grid-cols-2 xl:grid-cols-5 gap-3">
    <button
      v-for="card in cards"
      :key="card.key"
      type="button"
      class="text-left bg-card border rounded-2xl p-4 transition-all"
      :class="card.clickable
        ? (selectedStatus === card.status
          ? 'border-border bg-muted shadow-sm'
          : 'border-border hover:bg-accent')
        : 'border-border'"
      @click="card.clickable && emit('select-status', card.status)"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="text-xs text-muted-foreground/70">{{ card.label }}</p>
          <p class="text-2xl font-semibold text-foreground mt-2">{{ card.value }}</p>
        </div>
        <span class="h-2.5 w-2.5 rounded-full" :class="card.dotClass"></span>
      </div>
      <p class="text-2xs text-muted-foreground mt-3">{{ card.description }}</p>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SyncCenterOverview, SyncCenterStatusFilter } from '@/composables/useSyncCenter'

const props = defineProps<{
  overview: SyncCenterOverview
  selectedStatus: SyncCenterStatusFilter
}>()

const emit = defineEmits<{
  (e: 'select-status', status: SyncCenterStatusFilter): void
}>()

const cards = computed<Array<{
  key: string
  status: SyncCenterStatusFilter
  label: string
  value: number
  description: string
  dotClass: string
  clickable: boolean
}>>(() => ([
  {
    key: 'running',
    status: 'running',
    label: '运行中',
    value: props.overview.running_count,
    description: '当前正在被消费者处理的订阅',
    dotClass: 'bg-blue-500',
    clickable: true,
  },
  {
    key: 'queued',
    status: 'queued',
    label: '排队中',
    value: props.overview.queued_count,
    description: '已经入队，等待消费',
    dotClass: 'bg-amber-500',
    clickable: true,
  },
  {
    key: 'failed',
    status: 'failed',
    label: '失败待处理',
    value: props.overview.failed_count,
    description: '优先处理这批订阅',
    dotClass: 'bg-destructive',
    clickable: true,
  },
  {
    key: 'scheduled',
    status: 'scheduled',
    label: '即将执行',
    value: props.overview.due_soon_count,
    description: '未来 30 分钟内计划执行',
    dotClass: 'bg-emerald-500',
    clickable: true,
  },
  {
    key: 'queue-depth',
    status: 'scheduled',
    label: '队列积压',
    value: props.overview.queue_depth,
    description: `累计消息 ${props.overview.queue_messages}`,
    dotClass: 'bg-text-muted',
    clickable: false,
  },
]))
</script>

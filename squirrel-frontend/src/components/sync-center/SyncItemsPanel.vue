<template>
  <div class="overflow-hidden rounded-2xl border border-border-primary bg-bg-secondary">
    <div class="border-b border-border-primary px-3 py-2.5">
      <div class="flex items-center justify-between gap-3">
        <div>
          <div class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">{{ embedded ? '订阅影响面' : '同步项' }}</div>
          <div class="mt-1 text-2xs text-text-muted">共 {{ total }} 条</div>
        </div>
        <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
          第 {{ page }} / {{ totalPages }} 页
        </span>
      </div>

      <div v-if="!embedded" class="mt-3 flex flex-wrap gap-2">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          class="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
          :class="activeStatus === tab.value
            ? 'border-border-hover bg-bg-elevated text-text-primary'
            : 'border-border-primary bg-bg-primary text-text-muted hover:bg-bg-hover hover:text-text-primary'"
          @click="emit('change-status', tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="px-4 py-12 text-center text-sm text-text-muted">加载同步项中...</div>
    <div v-else-if="items.length === 0" class="px-4 py-12 text-center text-sm text-text-muted">当前条件下没有同步项</div>

    <div v-else-if="embedded" class="divide-y divide-border-primary">
      <button
        v-for="item in items"
        :key="`${item.subscription_id}-${item.sync_mode}-embedded`"
        type="button"
        class="w-full px-3 py-2.5 text-left transition-colors hover:bg-bg-hover"
        :class="selectedId === item.subscription_id ? 'bg-bg-hover' : ''"
        @click="emit('open-item', item)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="truncate text-xs font-medium text-text-primary">{{ item.subscription_name }}</span>
              <StatusBadge
                size="xs"
                :show-dot="false"
                :variant="getStatusVariant(item.display_status)"
                :label="getStatusLabel(item.display_status)"
                class="border-0"
              />
            </div>
            <div class="mt-1 truncate text-2xs text-text-tertiary">
              {{ item.site || 'unknown' }} · {{ item.sync_mode === 'full' ? '全量' : '增量' }}
            </div>
            <div class="mt-1 truncate text-2xs text-text-muted">{{ getSummary(item) }}</div>
          </div>
          <div class="shrink-0 text-right text-2xs text-text-secondary">
            <div>待处理 {{ item.pending_video_count || 0 }}</div>
            <div class="mt-1">失败 {{ item.failure_count || 0 }}</div>
          </div>
        </div>
      </button>
    </div>

    <div v-else>
      <div class="md:hidden divide-y divide-border-primary">
        <div v-for="item in items" :key="`${item.subscription_id}-${item.sync_mode}-mobile`" class="px-4 py-3">
          <button type="button" class="w-full text-left" @click="emit('open-item', item)">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="truncate text-sm font-medium text-text-primary">{{ item.subscription_name }}</span>
                  <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
                    {{ item.sync_mode === 'full' ? '全量' : '增量' }}
                  </span>
                </div>
                <div class="mt-1 text-2xs text-text-muted">{{ item.site || 'unknown' }}</div>
                <div class="mt-2 text-xs text-text-primary">{{ getSummary(item) }}</div>
              </div>
              <StatusBadge
                size="xs"
                :show-dot="false"
                :variant="getStatusVariant(item.display_status)"
                :label="getStatusLabel(item.display_status)"
                class="border-0"
              />
            </div>
          </button>
        </div>
      </div>

      <div class="hidden md:block overflow-x-auto">
        <table class="w-full min-w-[760px]">
          <thead class="border-b border-border-primary bg-bg-primary">
            <tr>
              <th class="px-4 py-2.5 text-left text-2xs font-semibold text-text-tertiary">订阅</th>
              <th class="px-4 py-2.5 text-left text-2xs font-semibold text-text-tertiary">状态</th>
              <th class="px-4 py-2.5 text-left text-2xs font-semibold text-text-tertiary">摘要</th>
              <th class="px-4 py-2.5 text-left text-2xs font-semibold text-text-tertiary">最后执行</th>
              <th class="px-4 py-2.5 text-right text-2xs font-semibold text-text-tertiary">待处理</th>
              <th class="px-4 py-2.5 text-right text-2xs font-semibold text-text-tertiary">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-primary">
            <tr
              v-for="item in items"
              :key="`${item.subscription_id}-${item.sync_mode}`"
              class="cursor-pointer transition-colors hover:bg-bg-hover"
              :class="selectedId === item.subscription_id ? 'bg-bg-hover' : ''"
              @click="emit('open-item', item)"
            >
              <td class="px-4 py-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="truncate text-xs font-medium text-text-primary">{{ item.subscription_name }}</span>
                    <span class="rounded-full border border-border-primary bg-bg-primary px-2 py-0.5 text-2xs text-text-tertiary">
                      {{ item.sync_mode === 'full' ? '全量' : '增量' }}
                    </span>
                  </div>
                  <div class="mt-1 text-2xs text-text-muted">{{ item.site || 'unknown' }}</div>
                </div>
              </td>
              <td class="px-4 py-3">
                <StatusBadge
                  size="xs"
                  :show-dot="false"
                  :variant="getStatusVariant(item.display_status)"
                  :label="getStatusLabel(item.display_status)"
                  class="border-0"
                />
              </td>
              <td class="px-4 py-3 text-2xs text-text-primary">{{ getSummary(item) }}</td>
              <td class="px-4 py-3 text-2xs text-text-secondary">{{ item.last_sync_at || item.updated_at || '从未执行' }}</td>
              <td class="px-4 py-3 text-right text-2xs text-text-primary">{{ item.pending_video_count || 0 }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-2" @click.stop>
                  <Button
                    size="xs"
                    shape="pill"
                    variant="secondary"
                    :loading="retryingId === item.subscription_id"
                    @click="emit('retry-item', item)"
                  >
                    重试
                  </Button>
                  <router-link
                    :to="`/subscription/${item.subscription_id}/all`"
                    class="rounded-full border border-border-primary bg-bg-primary px-3 py-1.5 text-xs text-text-secondary transition-colors hover:bg-bg-hover"
                  >
                    打开
                  </router-link>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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
import { Button, StatusBadge } from '@/components/common'
import type { SyncCenterItem, SyncCenterStatusFilter } from '@/composables/useSyncCenter'

const props = withDefaults(defineProps<{
  activeStatus: SyncCenterStatusFilter
  embedded?: boolean
  items: SyncCenterItem[]
  loading: boolean
  page: number
  pageSize: number
  retryingId: number | null
  selectedId?: number | null
  total: number
}>(), {
  embedded: false,
  selectedId: null,
})

const emit = defineEmits<{
  (e: 'change-page', page: number): void
  (e: 'change-status', status: SyncCenterStatusFilter): void
  (e: 'open-item', item: SyncCenterItem): void
  (e: 'retry-item', item: SyncCenterItem): void
}>()

const tabs: Array<{ value: SyncCenterStatusFilter; label: string }> = [
  { value: 'failed', label: '失败' },
  { value: 'running', label: '运行中' },
  { value: 'queued', label: '排队中' },
  { value: 'scheduled', label: '即将执行' },
  { value: 'recent', label: '最近活动' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'failed':
      return '失败'
    case 'running':
      return '运行中'
    case 'queued':
      return '排队中'
    case 'scheduled':
      return '即将执行'
    case 'deferred':
      return '已延后'
    default:
      return '正常'
  }
}

const getStatusVariant = (status: string) => {
  switch (status) {
    case 'failed':
      return 'error'
    case 'running':
      return 'info'
    case 'queued':
      return 'warning'
    case 'scheduled':
      return 'success'
    case 'deferred':
      return 'warning'
    default:
      return 'default'
  }
}

const getSummary = (item: SyncCenterItem) => {
  if (item.display_status === 'failed') {
    return item.last_error_summary || '最近同步失败'
  }
  if (item.display_status === 'running') {
    return item.pending_video_count > 0 ? `剩余 ${item.pending_video_count} 条` : '正在执行同步'
  }
  if (item.display_status === 'queued') {
    return item.queued_at ? `排队 ${item.queued_at}` : '等待消费者处理'
  }
  if (item.display_status === 'scheduled') {
    return item.next_sync_at ? `计划于 ${item.next_sync_at}` : '等待下一次调度'
  }
  if (item.display_status === 'deferred') {
    return item.last_error_summary || '因背压延后执行'
  }
  return item.last_success_at ? `最近成功 ${item.last_success_at}` : '状态正常'
}
</script>

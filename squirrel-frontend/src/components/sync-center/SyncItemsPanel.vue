<template>
  <div class="bg-bg-secondary border border-border-primary rounded-2xl overflow-hidden">
    <div class="px-4 py-3 border-b border-border-primary flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          class="px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
          :class="activeStatus === tab.value
            ? 'bg-bg-elevated text-text-primary border border-border-hover'
            : 'bg-bg-primary text-text-muted border border-border-primary hover:bg-bg-hover hover:text-text-primary'"
          @click="emit('change-status', tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="text-xs text-text-tertiary">共 {{ total }} 条</div>
    </div>

    <div v-if="loading" class="py-16 flex items-center justify-center">
      <div class="h-8 w-8 rounded-full border-2 border-border-primary border-t-text-primary animate-spin"></div>
    </div>

    <div v-else-if="items.length === 0" class="px-4 py-16 text-center text-text-muted">
      <p class="text-sm">当前筛选下没有同步项</p>
      <p class="text-xs mt-2">切换状态、站点或搜索关键字后会自动刷新。</p>
    </div>

    <div v-else>
      <div class="md:hidden divide-y divide-border-primary">
        <div
          v-for="item in items"
          :key="`${item.subscription_id}-${item.sync_mode}-mobile`"
          class="p-4 space-y-3"
        >
          <button
            type="button"
            class="w-full text-left"
            @click="emit('open-item', item)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-text-primary truncate">{{ item.subscription_name }}</span>
                  <span class="px-2 py-0.5 rounded-full text-2xs bg-bg-primary text-text-tertiary border border-border-primary">
                    {{ item.sync_mode === 'full' ? 'Full' : 'Incr' }}
                  </span>
                </div>
                <div class="text-2xs text-text-muted mt-1">{{ item.site || 'unknown' }}</div>
              </div>
              <StatusBadge
                size="xs"
                :show-dot="false"
                :variant="getStatusVariant(item.display_status)"
                :label="getStatusLabel(item.display_status)"
                class="border-0 shrink-0"
              />
            </div>
            <div class="text-xs text-text-primary mt-3">{{ getSummary(item) }}</div>
            <div class="grid grid-cols-2 gap-3 mt-3 text-2xs">
              <div>
                <div class="text-text-tertiary">最后执行</div>
                <div class="text-text-secondary mt-1">{{ item.last_sync_at || item.updated_at || '从未执行' }}</div>
              </div>
              <div>
                <div class="text-text-tertiary">下次执行</div>
                <div class="text-text-secondary mt-1">{{ item.next_sync_at || '—' }}</div>
              </div>
              <div>
                <div class="text-text-tertiary">待处理</div>
                <div class="text-text-secondary mt-1">{{ item.pending_video_count || 0 }}</div>
              </div>
              <div>
                <div class="text-text-tertiary">失败次数</div>
                <div class="text-text-secondary mt-1">{{ item.failure_count || 0 }}</div>
              </div>
            </div>
          </button>
          <div class="flex items-center gap-2">
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
              class="px-3 py-1.5 rounded-full text-xs bg-bg-primary text-text-secondary border border-border-primary hover:bg-bg-hover transition-colors"
            >
              打开订阅
            </router-link>
          </div>
        </div>
      </div>

      <div class="hidden md:block overflow-x-auto">
        <table class="w-full min-w-[820px]">
        <thead class="bg-bg-primary border-b border-border-primary">
          <tr>
            <th class="px-4 py-3 text-left text-2xs font-semibold text-text-tertiary">订阅</th>
            <th class="px-4 py-3 text-left text-2xs font-semibold text-text-tertiary">状态</th>
            <th class="px-4 py-3 text-left text-2xs font-semibold text-text-tertiary">摘要</th>
            <th class="px-4 py-3 text-left text-2xs font-semibold text-text-tertiary">最后执行</th>
            <th class="px-4 py-3 text-left text-2xs font-semibold text-text-tertiary">下次执行</th>
            <th class="px-4 py-3 text-right text-2xs font-semibold text-text-tertiary">待处理</th>
            <th class="px-4 py-3 text-right text-2xs font-semibold text-text-tertiary">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-primary">
          <tr
            v-for="item in items"
            :key="`${item.subscription_id}-${item.sync_mode}`"
            class="hover:bg-bg-hover transition-colors cursor-pointer"
            @click="emit('open-item', item)"
          >
            <td class="px-4 py-3">
              <div class="flex items-start gap-3">
                <img
                  v-if="item.subscription_avatar"
                  :src="item.subscription_avatar"
                  :alt="item.subscription_name"
                  class="w-10 h-10 rounded-full object-cover bg-bg-primary"
                  referrerpolicy="no-referrer"
                >
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-text-primary truncate">{{ item.subscription_name }}</span>
                    <span class="px-2 py-0.5 rounded-full text-2xs bg-bg-primary text-text-tertiary border border-border-primary">
                      {{ item.sync_mode === 'full' ? 'Full' : 'Incr' }}
                    </span>
                  </div>
                  <div class="text-2xs text-text-muted mt-1">{{ item.site || 'unknown' }}</div>
                </div>
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
            <td class="px-4 py-3">
              <div class="text-xs text-text-primary max-w-[20rem] truncate">{{ getSummary(item) }}</div>
              <div class="text-2xs text-text-tertiary mt-1">失败次数 {{ item.failure_count || 0 }}</div>
            </td>
            <td class="px-4 py-3 text-2xs text-text-secondary">
              {{ item.last_sync_at || item.updated_at || '从未执行' }}
            </td>
            <td class="px-4 py-3 text-2xs text-text-secondary">
              {{ item.next_sync_at || '—' }}
            </td>
            <td class="px-4 py-3 text-right text-xs text-text-primary">
              {{ item.pending_video_count || 0 }}
            </td>
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
                  class="px-3 py-1.5 rounded-full text-xs bg-bg-primary text-text-secondary border border-border-primary hover:bg-bg-hover transition-colors"
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

    <div v-if="totalPages > 1" class="px-4 py-3 border-t border-border-primary flex items-center justify-between">
      <span class="text-2xs text-text-tertiary">第 {{ page }} / {{ totalPages }} 页</span>
      <div class="flex items-center gap-2">
        <Button
          size="xs"
          shape="pill"
          variant="secondary"
          :disabled="page <= 1"
          @click="emit('change-page', page - 1)"
        >
          上一页
        </Button>
        <Button
          size="xs"
          shape="pill"
          variant="secondary"
          :disabled="page >= totalPages"
          @click="emit('change-page', page + 1)"
        >
          下一页
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, StatusBadge } from '@/components/common'
import type { SyncCenterItem, SyncCenterStatusFilter } from '@/composables/useSyncCenter'

const props = defineProps<{
  activeStatus: SyncCenterStatusFilter
  items: SyncCenterItem[]
  loading: boolean
  page: number
  pageSize: number
  retryingId: number | null
  total: number
}>()

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
    return item.pending_video_count > 0 ? `正在处理，剩余 ${item.pending_video_count} 条` : '正在执行同步'
  }
  if (item.display_status === 'queued') {
    return item.queued_at ? `排队时间 ${item.queued_at}` : '等待消费者处理'
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

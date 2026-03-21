<template>
  <Teleport to="body">
    <transition name="sync-drawer">
      <div
        v-if="open && item"
        class="fixed inset-0 z-50 flex justify-end bg-overlay-dark-50"
        @click.self="emit('close')"
      >
        <div class="w-full max-w-xl h-full bg-bg-primary border-l border-border-primary shadow-2xl flex flex-col">
          <div class="px-6 py-5 border-b border-border-primary flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-3">
                <img
                  v-if="item.subscription_avatar"
                  :src="item.subscription_avatar"
                  :alt="item.subscription_name"
                  class="w-12 h-12 rounded-full object-cover bg-bg-secondary"
                  referrerpolicy="no-referrer"
                >
                <div class="min-w-0">
                  <h2 class="text-lg font-semibold text-text-primary truncate">{{ item.subscription_name }}</h2>
                  <div class="flex items-center gap-2 mt-2">
                    <StatusBadge
                      size="xs"
                      :show-dot="false"
                      :variant="getStatusVariant(item.display_status)"
                      :label="getStatusLabel(item.display_status)"
                      class="border-0"
                    />
                    <span class="px-2 py-0.5 rounded-full text-2xs bg-bg-secondary text-text-tertiary border border-border-primary">
                      {{ item.sync_mode === 'full' ? 'Full' : 'Incremental' }}
                    </span>
                    <span class="text-2xs text-text-muted">{{ item.site || 'unknown' }}</span>
                  </div>
                </div>
              </div>
            </div>
            <button
              type="button"
              class="h-9 w-9 rounded-full bg-bg-secondary text-text-secondary hover:bg-bg-hover transition-colors"
              @click="emit('close')"
            >
              ✕
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-2xl bg-bg-secondary border border-border-primary p-4">
                <p class="text-2xs text-text-tertiary">失败次数</p>
                <p class="text-2xl font-semibold text-text-primary mt-2">{{ item.failure_count || 0 }}</p>
              </div>
              <div class="rounded-2xl bg-bg-secondary border border-border-primary p-4">
                <p class="text-2xs text-text-tertiary">待处理视频</p>
                <p class="text-2xl font-semibold text-text-primary mt-2">{{ item.pending_video_count || 0 }}</p>
              </div>
            </div>

            <div class="rounded-2xl bg-bg-secondary border border-border-primary p-5 space-y-4">
              <h3 class="text-sm font-medium text-text-primary">时间信息</h3>
              <div class="grid grid-cols-1 gap-3">
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-text-tertiary">最后执行</span>
                  <span class="text-text-primary">{{ item.last_sync_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-text-tertiary">最后成功</span>
                  <span class="text-text-primary">{{ item.last_success_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-text-tertiary">排队时间</span>
                  <span class="text-text-primary">{{ item.queued_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-text-tertiary">开始执行</span>
                  <span class="text-text-primary">{{ item.locked_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-text-tertiary">下次执行</span>
                  <span class="text-text-primary">{{ item.next_sync_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-text-tertiary">最近更新时间</span>
                  <span class="text-text-primary">{{ item.updated_at || '—' }}</span>
                </div>
              </div>
            </div>

            <div class="rounded-2xl bg-bg-secondary border border-border-primary p-5">
              <h3 class="text-sm font-medium text-text-primary">错误信息</h3>
              <pre class="mt-3 whitespace-pre-wrap break-all text-xs text-text-secondary bg-bg-primary border border-border-secondary rounded-xl p-4 min-h-[7rem]">{{ item.last_error || '当前没有错误信息' }}</pre>
            </div>
          </div>

          <div class="px-6 py-4 border-t border-border-primary flex items-center justify-end gap-3">
            <router-link
              :to="`/subscription/${item.subscription_id}/all`"
              class="px-4 py-2 rounded-full text-sm bg-bg-secondary text-text-primary border border-border-primary hover:bg-bg-hover transition-colors"
            >
              打开订阅
            </router-link>
            <Button
              size="sm"
              shape="pill"
              variant="secondary"
              @click="emit('close')"
            >
              关闭
            </Button>
            <Button
              size="sm"
              shape="pill"
              variant="primary"
              :loading="retrying"
              @click="emit('retry')"
            >
              立即重试
            </Button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { Button, StatusBadge } from '@/components/common'
import type { SyncCenterItem } from '@/composables/useSyncCenter'

defineProps<{
  item: SyncCenterItem | null
  open: boolean
  retrying: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'retry'): void
}>()

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
</script>

<style scoped>
.sync-drawer-enter-active,
.sync-drawer-leave-active {
  transition: opacity 180ms ease;
}

.sync-drawer-enter-from,
.sync-drawer-leave-to {
  opacity: 0;
}
</style>

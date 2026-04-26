<template>
  <section class="board-shell board-shell--recent">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">最近任务</p>
          <div class="h-px flex-1 bg-border/50"></div>
          <span class="board-count font-mono">{{ items.length.toString().padStart(2, '0') }}</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !items.length">
      <SyncBoardSkeleton :count="11" />
    </div>
    <div v-else-if="!items.length">
      <SyncBoardEmpty
        title="记录为空"
        message="当前没有最近提取结果"
      />
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <div
        v-for="item in items"
        :key="item.run_id || item.subscription_id"
        class="recent-row"
        :class="item.sync_status === 'failed' ? 'recent-row--failed' : ''"
      >
        <div class="recent-row__identity">
          <SubscriptionAvatar
            :src="item.subscription_avatar"
            :name="item.subscription_name"
            size="md"
          />

          <div class="recent-row__info">
            <div class="recent-row__title">
              <h3 class="truncate text-sm font-bold text-foreground/70">{{ item.subscription_name }}</h3>
            </div>
            <div class="recent-row__meta font-mono flex flex-wrap items-center gap-1.5 mt-0.5">
              <SiteIcon
                v-if="item.site"
                :icon-url="item.site_icon_url"
                :label="item.site"
                size="xs"
              />
              <span>{{ getSyncModeLabel(item.sync_mode) }}</span>
              <span class="opacity-10">·</span>
              <span>{{ formatDate(item.updated_at || item.last_success_at) }}</span>
            </div>
          </div>
        </div>

        <div class="recent-row__metrics">
          <div class="metric-group">
            <span class="metric-label">总数</span>
            <span class="metric-value font-mono">{{ item.batch_task_count }}</span>
          </div>
          <div class="metric-group">
            <span class="metric-label">完成</span>
            <span class="metric-value font-mono">{{ item.completed_task_count }}</span>
          </div>
          <div class="metric-group">
            <span class="metric-label">失败</span>
            <span
              class="metric-value font-mono"
              :class="item.failed_task_count > 0 ? 'text-rose-500' : ''"
            >
              {{ item.failed_task_count }}
            </span>
          </div>
        </div>
      </div>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SyncBoardEmpty from '@/components/sync-center/SyncBoardEmpty.vue'
import SyncBoardSkeleton from '@/components/sync-center/SyncBoardSkeleton.vue'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { formatDate } from '@/utils/dateFormat'
import { getSyncModeLabel } from '@/utils/syncMode'

defineProps<{
  items: SyncCenterItem[]
  loading: boolean
  error: string
}>()
</script>

<style scoped>
.board-shell {
  background: transparent;
  border-radius: 0;
  min-height: 0;
  border: none;
  display: flex;
  flex-direction: column;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-left: 0.5rem;
  color: hsl(var(--foreground) / 0.72);
}

.board-kicker {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: currentColor;
  opacity: 0.5;
}

.board-title {
  margin-top: 0.3rem;
  font-size: 1.25rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: hsl(var(--foreground) / 0.8);
}

.board-count {
  font-size: 12px;
  font-weight: 900;
  font-family: 'JetBrains Mono', monospace;
  color: currentColor;
  opacity: 0.8;
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: hsl(var(--border) / 0.4) transparent;
}

.board-list:hover {
  scrollbar-width: thin;
}

.board-list::-webkit-scrollbar {
  width: 4px;
  opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-default);
}

.board-list:hover::-webkit-scrollbar {
  opacity: 1;
}

.board-list::-webkit-scrollbar-track {
  background: transparent;
}

.board-list::-webkit-scrollbar-thumb {
  background: hsl(var(--border) / 0.4);
  border-radius: 2px;
}

.recent-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 3.5rem;
  background: transparent;
  padding: 0.5rem 0.75rem;
  text-align: left;
  border: none;
  position: relative;
  border-radius: 6px;
  transition: background var(--duration-normal) var(--ease-default);
  gap: 0.75rem;
}

.recent-row:hover {
  background: hsl(var(--background));
}

.recent-row--failed {
  background: oklch(70% 0.15 20 / 0.03);
}

.recent-row__identity {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  flex: 1;
}

.recent-row__info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
}

.recent-row__title {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.recent-row__title h3 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.recent-row__meta {
  font-size: 9px;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recent-row__metrics {
  display: flex;
  flex-direction: row;
  gap: 0.85rem;
  flex-shrink: 0;
  align-items: flex-end;
}

.recent-row--failed {
  background: oklch(70% 0.15 20 / 0.03);
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.metric-label {
  font-size: 7px;
  font-weight: 900;
  color: hsl(var(--muted-foreground) / 0.3);
  letter-spacing: 0.15em;
}

.metric-value {
  font-size: 12px;
  font-weight: 900;
  color: hsl(var(--foreground) / 0.6);
}

.lane-card-enter-active,
.lane-card-leave-active,
.lane-card-move {
  transition: all var(--duration-normal) var(--ease-default);
}

.lane-card-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.lane-card-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

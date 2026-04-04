<template>
  <section class="board-shell board-shell--recent">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">RECENT_TASKS</p>
          <div class="h-px flex-1 bg-white/5"></div>
          <span class="board-count font-mono">{{ items.length.toString().padStart(2, '0') }}</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !items.length">
      <SyncBoardSkeleton :count="6" />
    </div>
    <div v-else-if="!items.length">
      <SyncBoardEmpty 
        title="LOG_EMPTY"
        message="当前没有最近提取结果" 
      />
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <div
        v-for="(item, index) in items"
        :key="item.run_id || `${item.subscription_id}-${index}`"
        class="recent-row animate-scan"
        :class="item.sync_status === 'failed' ? 'recent-row--failed' : ''"
      >
        <div class="recent-row__main">
          <div class="recent-row__identity">
            <SubscriptionAvatar
              :src="item.subscription_avatar"
              :name="item.subscription_name"
              size="md"
            />

            <div class="min-w-0 flex-1">
              <div class="recent-row__title">
                <h3 class="truncate text-sm font-bold text-white/70">{{ item.subscription_name }}</h3>
              </div>
              <div class="recent-row__meta recent-row__meta--with-icon font-mono">
                <SiteIcon
                  v-if="item.site"
                  :icon-url="item.site_icon_url"
                  :label="item.site"
                  size="xs"
                  class="recent-row__site-icon"
                />
                <span>{{ item.site || 'unknown' }} · {{ formatDate(item.updated_at || item.last_success_at) }}</span>
              </div>
            </div>
          </div>

          <div class="metric-inline">
            <div class="metric-group">
              <span class="metric-label">TOTAL</span>
              <span class="metric-value font-mono">{{ item.batch_task_count }}</span>
            </div>
            <div class="metric-group">
              <span class="metric-label">DONE</span>
              <span class="metric-value font-mono">{{ item.completed_task_count }}</span>
            </div>
            <div class="metric-group">
              <span
                class="metric-label"
              >
                FAIL
              </span>
              <span
                class="metric-value font-mono"
                :class="item.failed_task_count > 0 ? 'text-rose-500' : ''"
              >
                {{ item.failed_task_count }}
              </span>
            </div>
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
  padding: 1.2rem;
  min-height: 0;
  border: none;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-left: 0.5rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--sci-fi-green);
  opacity: 0.5;
}

.board-title {
  margin-top: 0.3rem;
  font-size: 1.25rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.8);
}

.board-count {
  font-size: 12px;
  font-weight: 900;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sci-fi-green);
  opacity: 0.8;
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
}

.recent-row {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 4rem;
  background: transparent;
  padding: 0.6rem 1rem;
  text-align: left;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  position: relative;
}

.recent-row:hover {
  transform: translateX(6px);
  background: rgba(255, 255, 255, 0.02);
}

.recent-row--failed {
  border-left: 2px solid theme('colors.rose.500');
  background: oklch(70% 0.15 20 / 0.03);
}

.recent-row__main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.recent-row__identity {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
  flex: 1;
}

.recent-row__title {
  display: flex;
  align-items: center;
  min-width: 0;
}

.recent-row__meta {
  margin-top: 0.2rem;
  font-size: 9px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recent-row__meta--with-icon {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.recent-row__site-icon {
  opacity: 0.72;
}

.metric-inline {
  display: flex;
  flex-direction: row;
  gap: 1.5rem;
  flex-shrink: 0;
  align-items: flex-end;
  opacity: 0.5;
}

.recent-row:hover .metric-inline {
  opacity: 0.8;
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.metric-label {
  font-size: 6px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.2em;
}

.metric-value {
  font-size: 12px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.4);
}

.lane-card-enter-active,
.lane-card-leave-active,
.lane-card-move {
  transition: all 0.2s ease;
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

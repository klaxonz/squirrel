<template>
  <section class="board-shell board-shell--recent">
    <div class="board-header">
      <div>
        <p class="board-kicker">Lane 03</p>
        <h2 class="board-title">刚处理完</h2>
        <p class="board-caption">按最近结束时间倒序，显示最近完成或失败的视频提取批次。</p>
      </div>
      <span class="board-count">近 {{ items.length }} 条</span>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !items.length" class="board-empty">正在加载最近提取结果...</div>
    <div v-else-if="!items.length" class="board-empty">当前没有最近提取结果</div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <div
        v-for="(item, index) in items"
        :key="item.run_id || `${item.subscription_id}-${index}`"
        class="recent-row"
        :class="item.sync_status === 'failed' ? 'recent-row--failed' : ''"
      >
        <div class="recent-row__main">
          <div class="min-w-0 flex-1">
            <div class="recent-row__title">
              <span class="status-chip" :class="item.sync_status === 'failed' ? 'status-chip--failed' : 'status-chip--success'">
                {{ item.sync_status === 'failed' ? '失败' : '完成' }}
              </span>
              <span v-if="index === 0" class="latest-chip">最新</span>
              <h3 class="truncate text-sm font-semibold text-white/92">{{ item.subscription_name }}</h3>
            </div>
            <p class="recent-row__meta">
              {{ item.site || 'unknown' }} · {{ formatDate(item.updated_at || item.last_success_at) }} · {{ item.progress_label || '—' }}
            </p>
          </div>

          <div class="recent-row__summary">
            <span class="recent-row__percent">{{ item.progress_percent }}%</span>
          </div>
        </div>

        <div class="metric-inline">
          <span class="metric-pill">总数 {{ item.batch_task_count }}</span>
          <span class="metric-pill">完成 {{ item.completed_task_count }}</span>
          <span class="metric-pill">失败 {{ item.failed_task_count }}</span>
          <span class="metric-pill">剩余 {{ item.pending_video_count }}</span>
        </div>
      </div>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
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
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(126, 182, 255, 0.08), rgba(255, 255, 255, 0.02) 22%, rgba(0, 0, 0, 0.44));
  border-radius: 1.5rem;
  padding: 1.2rem;
  backdrop-filter: blur(12px);
  min-height: 0;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(157, 209, 255, 0.66);
}

.board-title {
  margin-top: 0.28rem;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: rgba(255, 255, 255, 0.94);
}

.board-caption {
  margin-top: 0.28rem;
  max-width: 20rem;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.44);
}

.board-count {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.44);
}

.board-empty,
.board-error {
  display: flex;
  min-height: 12rem;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  border: 1px dashed rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
  font-weight: 600;
}

.board-error {
  color: rgba(251, 113, 133, 0.86);
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
  padding-right: 0.15rem;
}

.recent-row {
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.025);
  padding: 0.8rem 0.85rem;
}

.recent-row--failed {
  border-color: rgba(251, 113, 133, 0.2);
}

.recent-row__main {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 0.75rem;
}

.recent-row__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.recent-row__meta {
  margin-top: 0.18rem;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-row__summary {
  display: flex;
  align-items: start;
  flex-shrink: 0;
}

.recent-row__percent {
  font-size: 1rem;
  font-weight: 700;
  line-height: 1;
  color: rgba(255, 255, 255, 0.9);
}

.status-chip,
.latest-chip,
.metric-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 700;
}

.status-chip {
  padding: 0.14rem 0.42rem;
}

.status-chip--success {
  background: rgba(74, 222, 128, 0.1);
  color: rgba(190, 255, 212, 0.92);
}

.status-chip--failed {
  background: rgba(251, 113, 133, 0.1);
  color: rgba(255, 203, 213, 0.92);
}

.latest-chip {
  padding: 0.14rem 0.4rem;
  background: rgba(126, 182, 255, 0.12);
  color: rgba(202, 227, 255, 0.92);
}

.metric-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-top: 0.62rem;
}

.metric-pill {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.62);
  padding: 0.22rem 0.48rem;
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

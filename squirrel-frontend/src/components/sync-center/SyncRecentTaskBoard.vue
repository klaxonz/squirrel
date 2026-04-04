<template>
  <section class="board-shell board-shell--recent">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">LANE_03</p>
          <div class="h-px flex-1 bg-white/5"></div>
          <span class="board-count font-mono">{{ items.length.toString().padStart(2, '0') }}</span>
        </div>
        <h2 class="board-title">RECENT_TASKS</h2>
      </div>
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
              <h3 class="truncate text-sm font-bold text-white/70">{{ item.subscription_name }}</h3>
              <span v-if="index === 0" class="latest-chip">NEW</span>
            </div>
            <p class="recent-row__meta font-mono">
              {{ item.site || 'unknown' }} · {{ formatDate(item.updated_at || item.last_success_at) }}
            </p>
          </div>
        </div>

        <div class="metric-inline mt-2 opacity-50 grayscale group-hover:grayscale-0 transition-all">
          <div class="metric-group">
            <span class="metric-label">TOTAL</span>
            <span class="metric-value font-mono text-[10px]">{{ item.batch_task_count }}</span>
          </div>
          <div class="metric-group">
            <span class="metric-label">DONE</span>
            <span class="metric-value font-mono text-[10px]">{{ item.completed_task_count }}</span>
          </div>
          <div class="metric-group">
            <span class="metric-label">FAIL</span>
            <span class="metric-value font-mono text-[10px]" :class="item.failed_task_count > 0 ? 'text-rose-500' : ''">{{ item.failed_task_count }}</span>
          </div>
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
  border: 1px solid var(--cyber-border);
  background: rgba(255, 255, 255, 0.02);
  border-radius: 0;
  padding: 1.2rem;
  backdrop-filter: blur(8px);
  min-height: 0;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.2rem;
  border-left: 2px solid rgba(255, 255, 255, 0.2);
  padding-left: 0.75rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.3);
}

.board-title {
  margin-top: 0.2rem;
  font-size: 1.1rem;
  font-weight: 900;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.95);
}

.board-caption {
  margin-top: 0.4rem;
  max-width: 20rem;
  font-size: 10px;
  line-height: 1.5;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.2);
}

.board-count {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.2);
}

.board-empty,
.board-error {
  display: flex;
  min-height: 12rem;
  align-items: center;
  justify-content: center;
  border-radius: 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.01);
  color: rgba(255, 255, 255, 0.25);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.board-error {
  color: rgba(251, 113, 133, 0.8);
  border-color: rgba(251, 113, 133, 0.2);
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.recent-row {
  display: flex;
  flex-direction: column;
  width: 100%;
  background: #050505;
  padding: 0.75rem 1rem;
  text-align: left;
  transition: all 0.2s ease;
  border: none;
}

.recent-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.recent-row--failed {
  border-left: 2px solid theme('colors.rose.500');
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
  min-width: 0;
}

.recent-row__meta {
  margin-top: 0.15rem;
  font-size: 9px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.2);
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.latest-chip {
  display: inline-flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.05rem 0.3rem;
  font-size: 8px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.05em;
  margin-left: 0.5rem;
}

.metric-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}

.metric-label {
  font-size: 6px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.2em;
}

.metric-value {
  font-weight: 800;
  color: rgba(255, 255, 255, 0.35);
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

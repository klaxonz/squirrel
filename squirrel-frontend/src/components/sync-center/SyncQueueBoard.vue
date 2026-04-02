<template>
  <section class="board-shell board-shell--queue">
    <div class="board-header">
      <div>
        <p class="board-kicker">Lane 01</p>
        <h2 class="board-title">接下来处理</h2>
        <p class="board-caption">严格按真实队列顺序展示。队首就是下一个进入中列的订阅。</p>
      </div>
      <span class="board-count">{{ items.length }} 项</span>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !items.length" class="board-empty">正在获取排队中的订阅...</div>
    <div v-else-if="!items.length" class="board-empty">当前没有排队中的订阅</div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <button
        v-for="(item, index) in items"
        :key="item.run_id || item.subscription_id"
        type="button"
        class="queue-row"
        :class="index === 0 ? 'queue-row--head' : ''"
        @click="emit('open-run', item)"
      >
        <div class="queue-row__rank">
          <span class="queue-row__rank-no">#{{ item.queue_position || '–' }}</span>
        </div>

        <div class="min-w-0 flex-1">
          <div class="queue-row__title">
            <span v-if="index === 0" class="queue-row__badge">队首</span>
            <h3 class="truncate text-sm font-semibold text-white/92">{{ item.subscription_name }}</h3>
          </div>
          <p class="queue-row__meta">
            {{ item.site || 'unknown' }} · {{ getModeLabel(item.sync_mode) }} · {{ formatDate(item.queued_at || item.updated_at) }}
          </p>
        </div>

        <div class="queue-row__flow" aria-hidden="true">
          <span class="queue-row__arrow">→</span>
          <span class="queue-row__flow-text">处理中</span>
        </div>
      </button>
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

const emit = defineEmits<{
  (e: 'open-run', item: SyncCenterItem): void
}>()

const getModeLabel = (mode: string) => {
  if (mode === 'full') return '全量'
  if (mode === 'incremental') return '增量'
  return mode || '未知'
}
</script>

<style scoped>
.board-shell {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 214, 102, 0.08), rgba(255, 255, 255, 0.02) 22%, rgba(0, 0, 0, 0.44));
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
  color: rgba(255, 214, 130, 0.66);
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

.queue-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.75rem;
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.025);
  padding: 0.78rem 0.85rem;
  text-align: left;
  transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.queue-row:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 214, 102, 0.24);
}

.queue-row--head {
  border-color: rgba(255, 214, 102, 0.28);
  background: rgba(255, 214, 102, 0.08);
}

.queue-row__rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.9rem;
  background: rgba(255, 214, 102, 0.1);
  flex-shrink: 0;
}

.queue-row__rank-no {
  font-size: 0.82rem;
  font-weight: 700;
  color: rgba(255, 235, 174, 0.94);
}

.queue-row__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.queue-row__badge {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  border: 1px solid rgba(255, 214, 102, 0.22);
  background: rgba(255, 214, 102, 0.1);
  padding: 0.12rem 0.42rem;
  font-size: 10px;
  font-weight: 700;
  color: rgba(255, 233, 170, 0.92);
  flex-shrink: 0;
}

.queue-row__meta {
  margin-top: 0.18rem;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-row__flow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.08rem;
  min-width: 3.1rem;
  flex-shrink: 0;
}

.queue-row__arrow {
  font-size: 1rem;
  font-weight: 700;
  color: rgba(255, 219, 133, 0.78);
}

.queue-row__flow-text {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
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

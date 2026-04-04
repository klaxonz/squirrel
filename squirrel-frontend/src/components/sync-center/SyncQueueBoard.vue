<template>
  <section class="board-shell board-shell--queue">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">LANE_01</p>
          <div class="h-px flex-1 bg-white/5"></div>
          <span class="board-count font-mono">{{ items.length.toString().padStart(2, '0') }}</span>
        </div>
        <h2 class="board-title">PENDING_QUEUE</h2>
      </div>
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
          <span class="queue-row__rank-no font-mono">#{{ (item.queue_position || index + 1).toString().padStart(2, '0') }}</span>
        </div>

        <div class="queue-row__identity">
          <div class="relative">
            <img
              :src="getAvatarSrc(item.subscription_avatar, item.subscription_id)"
              :alt="item.subscription_name"
              class="queue-row__avatar"
              referrerpolicy="no-referrer"
              @error="(event) => handleAvatarError(event, item.subscription_id)"
            >
            <div class="absolute -top-0.5 -left-0.5 w-1.5 h-1.5 rounded-full bg-[#00E5FF] glow-cyan"></div>
          </div>

          <div class="min-w-0 flex-1">
            <div class="queue-row__title">
              <span v-if="index === 0" class="queue-row__badge">队首</span>
              <h3 class="truncate text-sm font-bold text-white/90">{{ item.subscription_name }}</h3>
            </div>
            <p class="queue-row__meta font-mono">
              {{ item.site || 'unknown' }} · {{ getModeLabel(item.sync_mode) }} · {{ getQueueTimeLabel(item) }}
            </p>
          </div>
        </div>

        <div class="queue-row__flow" aria-hidden="true">
          <span class="queue-row__arrow text-[#00E5FF]">→</span>
          <span class="queue-row__flow-text">READY</span>
        </div>
      </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDate } from '@/utils/dateFormat'

defineProps<{
  items: SyncCenterItem[]
  loading: boolean
  error: string
}>()

const emit = defineEmits<{
  (e: 'open-run', item: SyncCenterItem): void
}>()

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()

const getModeLabel = (mode: string) => {
  if (mode === 'full') return '全量'
  if (mode === 'incremental') return '增量'
  return mode || '未知'
}

const getQueueTimeLabel = (item: SyncCenterItem) => {
  if (item.updated_at) {
    return `最近更新 ${formatDate(item.updated_at)}`
  }
  if (item.queued_at) {
    return `排队于 ${formatDate(item.queued_at)}`
  }
  return '最近更新 --'
}
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
  border-left: 2px solid var(--cyber-cyan);
  padding-left: 0.75rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--cyber-cyan);
  opacity: 0.7;
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
  color: rgba(255, 255, 255, 0.3);
}

.board-count {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  color: var(--cyber-cyan);
  opacity: 0.5;
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

.queue-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.75rem;
  background: #050505;
  padding: 0.75rem 0.85rem;
  text-align: left;
  transition: all 0.2s ease;
  border: none;
}

.queue-row:hover {
  background: rgba(255, 255, 255, 0.03);
  padding-left: 1.1rem;
}

.queue-row--head {
  border-left: 2px solid var(--cyber-cyan);
}

.queue-row__rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.1);
  flex-shrink: 0;
}

.queue-row__rank-no {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--cyber-cyan);
  opacity: 0.8;
}

.queue-row__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.queue-row__identity {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
  flex: 1;
}

.queue-row__avatar {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  filter: grayscale(0.2);
}

.queue-row__badge {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--cyber-cyan);
  background: rgba(0, 229, 255, 0.1);
  padding: 0.1rem 0.4rem;
  font-size: 9px;
  font-weight: 900;
  color: var(--cyber-cyan);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.queue-row__meta {
  margin-top: 0.2rem;
  font-size: 10px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-row__flow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  min-width: 3.5rem;
  flex-shrink: 0;
}

.queue-row__arrow {
  font-size: 1.1rem;
  font-weight: 900;
  opacity: 0.8;
}

.queue-row__flow-text {
  font-size: 8px;
  font-weight: 900;
  letter-spacing: 0.15em;
  color: rgba(255, 255, 255, 0.25);
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

<template>
  <section class="board-shell board-shell--queue">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">PENDING_QUEUE</p>
          <div class="h-px flex-1 bg-white/5"></div>
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
        title="QUEUE_CLEAR"
        message="当前没有排队中的订阅" 
      />
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
        <button
          v-for="(item, index) in items"
          :key="item.run_id || item.subscription_id"
          type="button"
          class="queue-row animate-scan"
          @click="emit('open-run', item)"
        >
          <div class="queue-row__main">
            <div class="queue-row__identity">
              <SubscriptionAvatar
                :src="item.subscription_avatar"
                :name="item.subscription_name"
                size="md"
              />

              <div class="min-w-0 flex-1">
                <div class="queue-row__title">
                  <h3 class="truncate text-sm font-bold text-white/90">{{ item.subscription_name }}</h3>
                </div>
                <p class="queue-row__meta font-mono inline-flex items-center gap-1.5 mt-1">
                  <SiteIcon
                    v-if="item.site"
                    :icon-url="getSiteIconUrl(item)"
                    :label="item.site"
                    size="xs"
                  />
                  {{ getModeLabel(item.sync_mode) }} · {{ getQueueTimeLabel(item) }}
                </p>
              </div>
            </div>
          </div>
        </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SyncBoardEmpty from '@/components/sync-center/SyncBoardEmpty.vue'
import SyncBoardSkeleton from '@/components/sync-center/SyncBoardSkeleton.vue'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { formatDate } from '@/utils/dateFormat'

const props = defineProps<{
  items: SyncCenterItem[]
  loading: boolean
  error: string
  siteOptions?: Array<{ value: string; label: string; iconUrl?: string | null }>
}>()

const emit = defineEmits<{
  (e: 'open-run', item: SyncCenterItem): void
}>()

const siteOptionMap = computed(() => {
  const m = new Map()
  for (const opt of (props.siteOptions || [])) {
    const value = String(opt.value || '').trim()
    if (!value) {
      continue
    }
    m.set(value, opt)
    m.set(value.toLowerCase(), opt)
  }
  return m
})

const getSiteIconUrl = (item: SyncCenterItem) => {
  const directIconUrl = String(item.site_icon_url || '').trim()
  if (directIconUrl) {
    return directIconUrl
  }

  const normalizedSite = String(item.site || '').trim()
  if (!normalizedSite) return null

  const fromMap = siteOptionMap.value.get(normalizedSite)?.iconUrl
    || siteOptionMap.value.get(normalizedSite.toLowerCase())?.iconUrl
  if (fromMap) return fromMap
  return `/api/plugins/sites/${encodeURIComponent(normalizedSite.toLowerCase())}/icon`
}

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
  color: var(--sci-fi-cyan);
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
  color: var(--sci-fi-cyan);
  opacity: 0.8;
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
}

.queue-row {
  display: flex;
  width: 100%;
  min-height: 3.5rem;
  align-items: center;
  gap: 1rem;
  background: transparent;
  padding: 0.6rem 1rem;
  text-align: left;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  position: relative;
}

.queue-row::before {
  content: "";
  position: absolute;
  inset: 0;
  background: white;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.queue-row:hover {
  transform: translateX(6px);
  background: rgba(255, 255, 255, 0.02);
}

.queue-row:hover::before {
  opacity: 0.02;
}

.queue-row__main {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.queue-row__identity {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
  flex: 1;
}

.queue-row__avatar {
  filter: grayscale(0.6) brightness(0.8);
  transition: all 0.3s ease;
}

.queue-row:hover .queue-row__avatar {
  filter: grayscale(0) brightness(1);
  transform: scale(1.05);
}

.queue-row__meta {
  margin-top: 0.25rem;
  font-size: 9px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.25);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.queue-row__arrow {
  font-size: 1rem;
  font-weight: 900;
}

.queue-row__flow-text {
  font-size: 7px;
  font-weight: 900;
  letter-spacing: 0.2em;
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

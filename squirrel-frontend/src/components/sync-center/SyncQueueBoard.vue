<template>
  <section class="board-shell board-shell--queue">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">排队队列</p>
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
        title="队列为空"
        message="当前没有排队中的订阅"
      />
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
        <button
          v-for="item in items"
          :key="item.run_id || item.subscription_id"
          type="button"
          class="queue-row animate-scan"
          @click="emit('open-run', item)"
        >
          <div class="queue-row__identity">
            <SubscriptionAvatar
              :src="item.subscription_avatar"
              :name="item.subscription_name"
              size="md"
            />

            <div class="queue-row__info">
              <div class="queue-row__title">
                <h3 class="truncate text-sm font-bold text-foreground">{{ item.subscription_name }}</h3>
              </div>
              <p class="queue-row__meta font-mono flex flex-wrap items-center gap-1.5 mt-0.5">
                <SiteIcon
                  v-if="item.site"
                  :icon-url="getSiteIconUrl(item)"
                  :label="item.site"
                  size="xs"
                />
                <span>{{ getSyncModeLabel(item.sync_mode) }}</span>
                <span class="opacity-30">·</span>
                <span>{{ getQueueTimeLabel(item) }}</span>
              </p>
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
import { getSyncModeLabel } from '@/utils/syncMode'

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
  transition: opacity 0.2s ease;
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

.queue-row {
  display: flex;
  width: 100%;
  min-height: 3.5rem;
  background: transparent;
  padding: 0.5rem 0.75rem;
  text-align: left;
  border: none;
  position: relative;
  border-radius: 6px;
  transition: background 0.2s ease;
  cursor: pointer;
}

.queue-row:hover {
  background: hsl(var(--background));
}

.queue-row__identity {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  width: 100%;
}

.queue-row__info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
}

.queue-row__title {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.queue-row__title h3 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.queue-row__meta {
  font-size: 9px;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.4);
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
  color: hsl(var(--muted-foreground) / 0.6);
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

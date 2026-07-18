<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="app-media-header">
      <div class="app-media-header__inner channel-header__inner">
        <div class="channel-header__identity">
          <a
            v-if="detail?.url"
            :href="detail.url"
            target="_blank"
            rel="noopener noreferrer"
            class="channel-header__avatar"
          >
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </a>
          <div v-else class="channel-header__avatar">
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </div>

          <div class="channel-header__copy">
            <div class="channel-header__title-row">
              <a
                v-if="detail?.url"
                :href="detail.url"
                target="_blank"
                rel="noopener noreferrer"
                class="channel-header__name-link"
              >
                <h1 class="app-h2 truncate">{{ detail?.name || '未知频道' }}</h1>
              </a>
              <h1 v-else class="app-h2 truncate">{{ detail?.name || '未知频道' }}</h1>
              <span v-if="detail?.is_nsfw" class="channel-header__badge">敏感</span>
            </div>

            <p v-if="detail?.description" class="channel-header__desc">
              {{ detail.description }}
            </p>

            <div class="channel-header__stats">
              <span class="channel-header__stat">
                <span class="channel-header__stat-label">总数</span>
                <span class="channel-header__stat-value">{{ detail?.total_videos || 0 }}</span>
              </span>
              <span class="channel-header__stat">
                <span class="channel-header__stat-label">解析</span>
                <span class="channel-header__stat-value">{{ detail?.total_extract || 0 }}</span>
              </span>
              <span v-if="pendingCount > 0" class="channel-header__stat">
                <span class="channel-header__stat-label">待处理</span>
                <span class="channel-header__stat-value">{{ pendingCount }}</span>
              </span>
            </div>

            <div
              v-if="syncStatusLine"
              class="channel-header__sync-status"
              :class="{ 'is-error': Boolean(detail?.last_error) }"
              :title="detail?.last_error || undefined"
            >
              {{ syncStatusLine }}
            </div>
          </div>
        </div>

        <div class="channel-header__actions">
          <AppSegmentedControl
            v-if="canOpenRemote"
            :model-value="mode || 'local'"
            :options="channelModeOptions"
            aria-label="频道内容来源"
            size="sm"
            @update:model-value="(value) => emit('update:mode', value)"
          />

          <Button
            type="button"
            text severity="secondary"
            size="sm" icon-only
            :class="detail?.is_special_followed ? 'text-warning' : ''"
            :disabled="isTogglingSpecial"
            aria-label="切换特别关注"
            :aria-pressed="!!detail?.is_special_followed"
            @click="handleToggleSpecialFollow"
          >
            <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': detail?.is_special_followed }" />
          </Button>

          <div v-if="syncMessage" class="channel-header__sync-msg" :class="syncError ? 'is-error' : ''">
            {{ syncMessage }}
          </div>

          <div class="channel-sync-group">
            <Button
              type="button"
              text severity="secondary"
              size="sm"
              :disabled="isSyncing"
              @click="handleDirectSync('incremental')"
            >
              <AppSpinner v-if="isSyncing" size="sm" />
              <AppIcon v-else name="refresh" class="h-3.5 w-3.5" />
              {{ isSyncing ? '同步中' : '同步' }}
            </Button>
            <AppActionMenu
              :items="syncMenuItems"
              :disabled="isSyncing"
              trigger-label="选择同步模式"
              icon="chevronDown"
            />
          </div>

          <Button
            type="button"
            severity="danger"
            size="sm"
            :disabled="isUnsubscribing"
            @click="handleUnsubscribe"
          >
            {{ isUnsubscribing ? '取消中' : '取消订阅' }}
          </Button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import { Button } from '@/shared/ui/button'
import { getSubscriptionDetail, triggerDirectRefresh, unsubscribe as apiUnsubscribe, updateSpecialFollowStatus } from '@/shared/api'
import { notifySubscriptionRemoved } from '@/shared/lib/subscriptionEvents'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'

const props = defineProps({
  subscriptionId: { type: [String, Number], required: true },
  mode: { type: String, default: undefined }
})

const emit = defineEmits(['update:mode', 'loaded', 'synced'])
const channelModeOptions = [
  { value: 'local', label: '本地' },
  { value: 'remote', label: '远端' },
]

const detail = ref(null);
const loading = ref(false);
const isVisible = ref(true)
const isUnsubscribing = ref(false)
const isTogglingSpecial = ref(false)
const isSyncing = ref(false)
const unsubscribeError = ref('')
const syncError = ref('')
const syncMessage = ref('')
const DISMISS_MS = 180
const isDesktop = useDesktopBridge().isDesktop()

const syncMenuItems = computed(() => [
  { label: '增量同步', appIcon: 'refresh', command: () => handleDirectSync('incremental') },
  { label: '全量同步', appIcon: 'sync', command: () => handleDirectSync('full') },
])

const canOpenRemote = computed(() => {
  return isDesktop && !!detail.value?.site && !!detail.value?.url
})

const pendingCount = computed(() => Number(detail.value?.pending_video_count || 0))

const formatSyncTime = (value) => {
  if (!value) return ''
  const text = String(value).trim()
  if (!text) return ''
  // Backend uses "YYYY-MM-DD HH:MM:SS"; show a compact local-friendly form.
  return text.length >= 16 ? text.slice(0, 16) : text
}

const syncStatusLine = computed(() => {
  const d = detail.value
  if (!d) return ''
  const status = String(d.sync_status || '').toLowerCase()
  if (status === 'running' || status === 'syncing') return '同步中'
  if (status === 'queued' || status === 'pending') return '排队中'
  if (d.last_error) {
    const err = String(d.last_error)
    return err.length > 80 ? `同步失败：${err.slice(0, 80)}…` : `同步失败：${err}`
  }
  const lastOk = formatSyncTime(d.last_success_at)
  if (lastOk) return `上次成功：${lastOk}`
  return ''
})

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const fetchDetail = async () => {
  if (!props.subscriptionId) return;
  loading.value = true;
  try {
    const data = await getSubscriptionDetail(props.subscriptionId);
    detail.value = data;
    emit('loaded', data)
  } catch {
    // silent — failed detail fetch leaves the prior detail
  } finally {
    loading.value = false;
  }
};

const handleUnsubscribe = async () => {
  if (!props.subscriptionId || isUnsubscribing.value) return

  isUnsubscribing.value = true
  unsubscribeError.value = ''

  try {
    await apiUnsubscribe(props.subscriptionId)
    isVisible.value = false
    notifySubscriptionRemoved(props.subscriptionId)
    await wait(DISMISS_MS)
  } catch (err) {
    unsubscribeError.value = errorMessage(err, '取消订阅失败')
  } finally {
    isUnsubscribing.value = false
  }
}

const handleToggleSpecialFollow = async () => {
  if (!props.subscriptionId || !detail.value || isTogglingSpecial.value) return

  isTogglingSpecial.value = true
  const nextValue = !detail.value.is_special_followed
  try {
    await updateSpecialFollowStatus(props.subscriptionId, nextValue)
    detail.value = { ...detail.value, is_special_followed: nextValue }
    emit('loaded', detail.value)
  } catch {
    // silent — toggle failure leaves the prior special-follow state
  } finally {
    isTogglingSpecial.value = false
  }
}

const buildSyncSuccessMessage = (data, mode) => {
  if (data?.status === 'in_progress') return '同步进行中'
  if (data?.status === 'queued') return '同步等待中'
  if (data?.skippedReason) return '同步已跳过'
  const found = Number(data?.videosFound || 0)
  const extracted = Number(data?.videosExtracted || 0)
  const modeLabel = mode === 'full' ? '全量' : '增量'
  return `${modeLabel}完成 ${extracted}/${found}`
}

const handleDirectSync = async (mode = 'incremental') => {
  if (!props.subscriptionId || isSyncing.value) return

  isSyncing.value = true
  syncError.value = ''
  syncMessage.value = ''

  try {
    const data = await triggerDirectRefresh(props.subscriptionId, mode)
    syncMessage.value = buildSyncSuccessMessage(data, mode)
    await fetchDetail()
    emit('synced', data)
  } catch (err) {
    syncError.value = errorMessage(err, '同步失败')
    syncMessage.value = syncError.value
  } finally {
    isSyncing.value = false
  }
}

watch(() => props.subscriptionId, () => {
  isVisible.value = true
  isUnsubscribing.value = false
  isTogglingSpecial.value = false
  unsubscribeError.value = ''
  isSyncing.value = false
  syncError.value = ''
  syncMessage.value = ''
  fetchDetail()
}, { immediate: true })
</script>

<style scoped>
.channel-header__inner {
  --app-page-max-width: var(--app-content-media-max);
  align-items: flex-start;
  gap: var(--space-5);
}

.channel-header__identity {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: flex-start;
  gap: var(--space-4);
}

.channel-header__avatar {
  display: block;
  width: 3.5rem;
  height: 3.5rem;
  flex: none;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--muted));
}

.channel-header__copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.375rem;
}

.channel-header__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.channel-header__name-link {
  min-width: 0;
  color: inherit;
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-default);
}

.channel-header__name-link:hover {
  color: hsl(var(--foreground));
}

.channel-header__badge {
  flex: none;
  border: 1px solid hsl(var(--primary) / 0.35);
  border-radius: var(--radius-sm);
  background: hsl(var(--primary) / 0.08);
  padding: 0.125rem 0.375rem;
  color: hsl(var(--primary));
  font-size: 0.6875rem;
  font-weight: 650;
}

.channel-header__desc {
  margin: 0;
  max-width: 42rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.channel-header__sync-status {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.4;
}

.channel-header__sync-status.is-error {
  color: hsl(var(--destructive));
}

.channel-header__stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4);
}

.channel-header__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.375rem;
}

.channel-header__stat-label {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.channel-header__stat-value {
  color: hsl(var(--foreground));
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.channel-header__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.channel-header__sync-msg {
  max-width: 10rem;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.channel-header__sync-msg.is-error {
  color: hsl(var(--destructive));
}

.channel-sync-group {
  display: flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--app-control-border);
  border-radius: var(--app-control-radius);
  background: var(--app-control-bg);
  padding: 2px;
}

.channel-dismiss-enter-active,
.channel-dismiss-leave-active {
  transition:
    opacity var(--duration-base) var(--ease-out),
    transform var(--duration-base) var(--ease-out);
}

.channel-dismiss-enter-from,
.channel-dismiss-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}

@media (prefers-reduced-motion: reduce) {
  .channel-dismiss-enter-active,
  .channel-dismiss-leave-active {
    transition: none;
  }

  .channel-dismiss-enter-from,
  .channel-dismiss-leave-to {
    transform: none;
  }
}
</style>

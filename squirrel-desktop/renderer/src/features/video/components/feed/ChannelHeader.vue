<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="app-media-header">
      <div class="app-media-header__inner channel-header__inner">
        <div v-if="loading && !detail" class="channel-header__identity channel-header__skeleton" aria-label="频道信息加载中" role="status">
          <AppSkeleton width="3.5rem" height="3.5rem" radius="var(--app-surface-radius)" />
          <div class="channel-header__skeleton-copy">
            <AppSkeleton width="12rem" height="1.5rem" />
            <AppSkeleton width="20rem" height="0.875rem" />
            <AppSkeleton width="9rem" height="0.75rem" />
          </div>
        </div>

        <div v-else-if="detail" class="channel-header__identity">
          <a v-if="detail.url" :href="detail.url" target="_blank" rel="noopener noreferrer" class="channel-header__avatar">
            <SubscriptionAvatar :src="detail.avatar || null" :name="detail.name || '未知频道'" size="full" />
          </a>
          <div v-else class="channel-header__avatar">
            <SubscriptionAvatar :src="detail.avatar || null" :name="detail.name || '未知频道'" size="full" />
          </div>

          <div class="channel-header__copy">
            <div class="channel-header__title-row">
              <a v-if="detail.url" :href="detail.url" target="_blank" rel="noopener noreferrer" class="channel-header__name-link">
                <h1 class="app-h2 truncate">{{ detail.name || '未知频道' }}</h1>
              </a>
              <h1 v-else class="app-h2 truncate">{{ detail.name || '未知频道' }}</h1>
              <span v-if="detail.is_nsfw" class="channel-header__badge">敏感</span>
            </div>

            <p v-if="detail.description" class="channel-header__desc">{{ detail.description }}</p>

            <div class="channel-header__stats">
              <span class="channel-header__stat">
                <span class="channel-header__stat-label">总数</span>
                <span class="channel-header__stat-value">{{ detail.total_videos || 0 }}</span>
              </span>
              <span class="channel-header__stat">
                <span class="channel-header__stat-label">解析</span>
                <span class="channel-header__stat-value">{{ detail.total_extract || 0 }}</span>
              </span>
            </div>

            <div v-if="syncContext.length" class="channel-header__sync-context" aria-label="同步状态">
              <span
                v-for="item in syncContext"
                :key="item.label"
                class="channel-header__sync-status"
                :class="{ 'is-error': item.error }"
                :title="item.title"
              >
                <span class="channel-header__sync-label">{{ item.label }}</span>{{ item.value }}
              </span>
            </div>
          </div>
        </div>

        <div v-else class="channel-header__identity channel-header__identity--error" role="alert">
          <AppIcon name="warning" class="h-5 w-5" />
          <div>
            <strong>频道信息加载失败</strong>
            <p>{{ detailError }}</p>
          </div>
          <Button type="button" severity="secondary" outlined size="sm" :disabled="loading" @click="fetchDetail">重试</Button>
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

          <span v-if="loading && detail" class="channel-header__refreshing" role="status">正在更新频道信息</span>

          <Button
            type="button"
            text severity="secondary"
            size="sm" icon-only
            :class="detail?.is_special_followed ? 'text-warning' : ''"
            :disabled="!detail || isTogglingSpecial"
            aria-label="切换特别关注"
            :aria-pressed="!!detail?.is_special_followed"
            @click="handleToggleSpecialFollow"
          >
            <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': detail?.is_special_followed }" />
          </Button>

          <div v-if="syncMessage" class="channel-header__sync-msg" :class="syncError ? 'is-error' : ''">{{ syncMessage }}</div>

          <div class="channel-sync-group">
            <Button type="button" text severity="secondary" size="sm" :disabled="isSyncing" @click="handleDirectSync('incremental')">
              <AppSpinner v-if="isSyncing" size="sm" />
              <AppIcon v-else name="refresh" class="h-3.5 w-3.5" />
              {{ isSyncing ? '同步中' : '同步' }}
            </Button>
            <AppActionMenu :items="syncMenuItems" :disabled="isSyncing" trigger-label="选择同步模式" icon="chevronDown" />
          </div>

          <Button type="button" severity="danger" size="sm" :disabled="isUnsubscribing" @click="confirmUnsubscribeOpen = true">
            {{ isUnsubscribing ? '取消中' : '取消订阅' }}
          </Button>
        </div>
      </div>

      <div v-if="actionError" class="channel-header__action-error" role="alert">
        <AppIcon name="warning" class="h-4 w-4" />
        <span>{{ actionError }}</span>
        <Button type="button" text severity="secondary" size="sm" aria-label="关闭操作错误" @click="actionError = ''">
          <AppIcon name="close" class="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  </transition>

  <ConfirmDialog
    v-model:open="confirmUnsubscribeOpen"
    icon="trash"
    icon-bg-class="bg-destructive/10"
    icon-class="text-destructive"
    title="取消频道订阅"
    :description="`取消订阅后，${detail?.name || '该频道'}将从订阅列表中移除。`"
    cancel-label="保留订阅"
    confirm-label="取消订阅"
    confirm-variant="destructive"
    :confirming="isUnsubscribing"
    @confirm="handleUnsubscribe"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
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

const emit = defineEmits(['update:mode', 'loaded', 'synced', 'state-change'])
const channelModeOptions = [
  { value: 'local', label: '本地' },
  { value: 'remote', label: '远端' },
]

const detail = ref(null);
const loading = ref(false);
const detailError = ref('')
const isVisible = ref(true)
const confirmUnsubscribeOpen = ref(false)
const isUnsubscribing = ref(false)
const isTogglingSpecial = ref(false)
const isSyncing = ref(false)
const actionError = ref('')
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

const syncContext = computed(() => {
  const d = detail.value
  if (!d) return []
  const result = []
  const status = String(d.sync_status || '').toLowerCase()
  if (status === 'running' || status === 'syncing') result.push({ label: '状态', value: '同步中' })
  else if (status === 'queued' || status === 'pending') result.push({ label: '状态', value: '排队中' })
  if (d.last_error) {
    const err = String(d.last_error)
    result.push({
      label: '上次同步',
      value: err.length > 80 ? `失败：${err.slice(0, 80)}…` : `失败：${err}`,
      error: true,
      title: err,
    })
  } else {
    const lastOk = formatSyncTime(d.last_success_at || d.last_sync_at)
    if (lastOk) result.push({ label: '上次同步', value: lastOk })
  }
  const nextSync = formatSyncTime(d.next_sync_at)
  if (nextSync) result.push({ label: '下次同步', value: nextSync })
  if (pendingCount.value > 0) result.push({ label: '待处理', value: `${pendingCount.value} 个视频` })
  return result
})

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

let detailRequestToken = 0
const fetchDetail = async () => {
  if (!props.subscriptionId) return
  const requestToken = ++detailRequestToken
  loading.value = true
  detailError.value = ''
  emit('state-change', { loading: true, error: '' })
  try {
    const data = await getSubscriptionDetail(props.subscriptionId)
    if (requestToken !== detailRequestToken) return
    detail.value = data
    emit('loaded', data)
  } catch (err) {
    if (requestToken !== detailRequestToken) return
    detailError.value = errorMessage(err, '频道信息加载失败')
  } finally {
    if (requestToken === detailRequestToken) {
      loading.value = false
      emit('state-change', { loading: false, error: detailError.value })
    }
  }
}

const handleUnsubscribe = async () => {
  if (!props.subscriptionId || isUnsubscribing.value) return

  isUnsubscribing.value = true
  actionError.value = ''

  try {
    await apiUnsubscribe(props.subscriptionId)
    confirmUnsubscribeOpen.value = false
    isVisible.value = false
    notifySubscriptionRemoved(props.subscriptionId)
    await wait(DISMISS_MS)
  } catch (err) {
    actionError.value = errorMessage(err, '取消订阅失败')
  } finally {
    isUnsubscribing.value = false
  }
}

const handleToggleSpecialFollow = async () => {
  if (!props.subscriptionId || !detail.value || isTogglingSpecial.value) return

  isTogglingSpecial.value = true
  actionError.value = ''
  const nextValue = !detail.value.is_special_followed
  try {
    await updateSpecialFollowStatus(props.subscriptionId, nextValue)
    detail.value = { ...detail.value, is_special_followed: nextValue }
    emit('loaded', detail.value)
  } catch (err) {
    actionError.value = errorMessage(err, '特别关注更新失败')
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
  detailRequestToken += 1
  detail.value = null
  isVisible.value = true
  confirmUnsubscribeOpen.value = false
  isUnsubscribing.value = false
  isTogglingSpecial.value = false
  actionError.value = ''
  isSyncing.value = false
  syncError.value = ''
  syncMessage.value = ''
  fetchDetail()
}, { immediate: true })

defineExpose({ refresh: fetchDetail })
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

.channel-header__skeleton-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.125rem;
}

.channel-header__identity--error {
  align-items: center;
  color: hsl(var(--destructive));
}

.channel-header__identity--error p {
  margin: 0.125rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
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
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.4);
  padding: 0.125rem 0.375rem;
  color: hsl(var(--muted-foreground));
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

.channel-header__sync-context {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
  margin-top: 0.125rem;
}

.channel-header__sync-status {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.4;
}

.channel-header__sync-label {
  margin-right: 0.25rem;
  font-weight: 600;
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

.channel-header__refreshing {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.channel-header__action-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: min(var(--app-content-media-max), 100%);
  margin: 0 auto;
  padding: 0.5rem var(--app-page-gutter);
  border-top: 1px solid hsl(var(--destructive) / 0.2);
  color: hsl(var(--destructive));
  font-size: 0.8125rem;
}

.channel-header__action-error span {
  flex: 1;
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

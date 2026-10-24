<template>
  <transition name="channel-dismiss">
    <ChannelIdentityHeader
      v-if="isVisible"
      :loading="loading"
      :name="detail?.name"
      :avatar="detail?.avatar"
      :url="detail?.url"
      :description="detail?.description"
      :badge="detail?.is_nsfw ? '敏感' : null"
      :error="detailError"
      error-title="频道信息加载失败"
      loading-label="频道信息加载中"
      name-fallback="未知频道"
      root-class="channel-header"
      @retry="fetchDetail"
    >
      <template #stats>
        <span class="channel-header__stat">
          <span class="channel-header__stat-label">总数</span>
          <span class="channel-header__stat-value">{{ detail?.total_videos || 0 }}</span>
        </span>
        <span class="channel-header__stat">
          <span class="channel-header__stat-label">解析</span>
          <span class="channel-header__stat-value">{{ detail?.total_extract || 0 }}</span>
        </span>

        <span
          v-for="item in syncContext"
          :key="item.label"
          class="channel-header__sync-status"
          :class="{ 'is-error': item.error }"
          :title="item.title"
        >
          <span class="channel-header__sync-label">{{ item.label }}</span>{{ item.value }}
        </span>
      </template>

      <template #actions>
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
          variant="secondary"
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
          <Button type="button" variant="secondary" size="sm" :disabled="isSyncing" @click="handleDirectSync('incremental')">
            <AppSpinner v-if="isSyncing" size="sm" />
            <AppIcon v-else name="refresh" class="h-3.5 w-3.5" />
            {{ isSyncing ? '同步中' : '同步' }}
          </Button>
          <AppActionMenu :items="syncMenuItems" :disabled="isSyncing" trigger-label="选择同步模式" icon="chevronDown" />
        </div>

        <Button type="button" variant="destructive" size="sm" :disabled="isUnsubscribing" @click="confirmUnsubscribeOpen = true">
          {{ isUnsubscribing ? '取消中' : '取消订阅' }}
        </Button>
      </template>

      <template #footer>
        <div v-if="actionError" class="channel-header__action-error" role="alert">
          <AppIcon name="warning" class="h-4 w-4" />
          <span>{{ actionError }}</span>
          <Button type="button" variant="secondary" size="sm" aria-label="关闭操作错误" @click="actionError = ''">
            <AppIcon name="close" class="h-3.5 w-3.5" />
          </Button>
        </div>
      </template>
    </ChannelIdentityHeader>
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
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import ChannelIdentityHeader from '@/features/video/components/feed/ChannelIdentityHeader.vue'
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
.channel-header__sync-status {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.4;
}

.channel-header__sync-label {
  margin-right: 0.25rem;
  font-weight: 600;
}

.channel-header__sync-status.is-error {
  color: hsl(var(--destructive));
}

.channel-header__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3rem;
}

.channel-header__stat-label {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 500;
}

.channel-header__stat-value {
  color: hsl(var(--foreground));
  font-family: var(--font-numeric);
  font-size: var(--app-text-sm);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.channel-header__refreshing {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.channel-header__action-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  max-width: var(--app-content-media-max);
  margin: 0 auto;
  padding: 0.5rem var(--app-content-media-gutter);
  border-top: 1px solid hsl(var(--destructive) / 0.2);
  color: hsl(var(--destructive));
  font-size: var(--app-text-md);
}

.channel-header__action-error span {
  flex: 1;
}

.channel-header__sync-msg {
  max-width: 10rem;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
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

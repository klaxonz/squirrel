<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="app-media-header">
      <div class="app-media-header__inner channel-header__inner">
        
        <div class="flex items-center gap-4 min-w-0">
          <!-- Avatar -->
          <a
            v-if="detail?.url"
            :href="detail.url"
            target="_blank"
            rel="noopener noreferrer"
            class="shrink-0 h-12 w-12 overflow-hidden rounded-lg sm:h-14 sm:w-14"
          >
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </a>
          <div v-else class="shrink-0 h-12 w-12 overflow-hidden rounded-lg sm:h-14 sm:w-14">
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </div>

          <!-- Info -->
          <div class="flex flex-col gap-1 min-w-0">
            <div class="flex items-center gap-2 min-w-0">
              <a
                v-if="detail?.url"
                :href="detail.url"
                target="_blank"
                rel="noopener noreferrer"
                class="hover:text-primary transition-colors min-w-0"
              >
                <h2 class="app-h2 truncate">{{ detail?.name || '未知频道' }}</h2>
              </a>
              <h2 v-else class="app-h2 truncate">{{ detail?.name || '未知频道' }}</h2>
              
              <span v-if="detail?.is_nsfw" class="shrink-0 rounded-md border border-primary/50 px-1.5 py-0.5 text-xs font-semibold text-primary">敏感</span>
            </div>
            
            <p v-if="detail?.description" class="text-xs text-muted-foreground/80 line-clamp-1 sm:line-clamp-2 max-w-2xl leading-relaxed">
              {{ detail.description }}
            </p>
          </div>
        </div>

        <!-- Stats & Actions -->
        <div class="flex items-center gap-6 sm:gap-8 shrink-0 ml-16 sm:ml-0">
          <div class="flex items-center gap-4 sm:gap-6">
            <div class="flex flex-col items-center">
              <span class="mb-1 text-xs font-medium text-muted-foreground">总数</span>
              <span class="text-sm font-semibold font-mono text-foreground/80">{{ detail?.total_videos || 0 }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="mb-1 text-xs font-medium text-muted-foreground">解析</span>
              <span class="text-sm font-semibold font-mono text-foreground/80">{{ detail?.total_extract || 0 }}</span>
            </div>
          </div>

          <AppSegmentedControl
            v-if="canOpenRemote"
            :model-value="mode || 'local'"
            :options="channelModeOptions"
            aria-label="频道内容来源"
            size="sm"
            @update:model-value="(value) => emit('update:mode', value)"
          />

          <div class="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              :class="detail?.is_special_followed ? 'text-warning' : ''"
              :disabled="isTogglingSpecial"
              aria-label="切换特别关注"
              :aria-pressed="!!detail?.is_special_followed"
              @click="handleToggleSpecialFollow"
            >
              <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': detail?.is_special_followed }" />
            </Button>
            <div v-if="syncMessage" class="hidden max-w-40 truncate text-xs font-medium sm:block" :class="syncError ? 'text-destructive' : 'text-muted-foreground'">
              {{ syncMessage }}
            </div>
            <div class="channel-sync-group">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                :disabled="isSyncing"
                @click="handleDirectSync('incremental')"
              >
                <AppSpinner v-if="isSyncing" size="sm" />
                <AppIcon v-else name="refresh" class="h-3.5 w-3.5" />
                {{ isSyncing ? '同步中' : '同步' }}
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    :disabled="isSyncing"
                    aria-label="选择同步模式"
                  >
                    <AppIcon name="chevronDown" class="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" class="w-36">
                  <DropdownMenuItem @click="handleDirectSync('incremental')">
                    <AppIcon name="refresh" class="mr-2 h-3.5 w-3.5" />
                    增量同步
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="handleDirectSync('full')">
                    <AppIcon name="sync" class="mr-2 h-3.5 w-3.5" />
                    全量同步
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <Button
            type="button"
            variant="destructive"
            size="sm"
            :disabled="isUnsubscribing"
            @click="handleUnsubscribe"
          >
            {{ isUnsubscribing ? '取消中...' : '取消订阅' }}
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
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import { Button } from '@/shared/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'
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

const canOpenRemote = computed(() => {
  return isDesktop && !!detail.value?.site && !!detail.value?.url
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
  --app-page-max-width: 2400px;
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
  transition: all var(--duration-slow) var(--ease-out);
}

.channel-dismiss-enter-from,
.channel-dismiss-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>

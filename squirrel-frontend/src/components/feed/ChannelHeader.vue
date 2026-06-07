<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="relative bg-background border-b border-border/20 overflow-hidden">
      <div class="max-w-[2560px] mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        
        <div class="flex items-center gap-4 min-w-0">
          <!-- Avatar -->
          <a
            v-if="detail?.url"
            :href="detail.url"
            target="_blank"
            rel="noopener noreferrer"
            class="shrink-0 h-12 w-12 overflow-hidden rounded-full sm:h-14 sm:w-14"
          >
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </a>
          <div v-else class="shrink-0 h-12 w-12 overflow-hidden rounded-full sm:h-14 sm:w-14">
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
                <h2 class="text-base sm:text-lg font-bold text-foreground truncate tracking-tight">{{ detail?.name || '未知频道' }}</h2>
              </a>
              <h2 v-else class="text-base sm:text-lg font-bold text-foreground truncate tracking-tight">{{ detail?.name || '未知频道' }}</h2>
              
              <span v-if="detail?.is_nsfw" class="shrink-0 px-1.5 py-0.5 text-[10px] font-bold tracking-widest uppercase border border-primary/50 text-primary rounded-md">NSFW</span>
            </div>
            
            <p v-if="detail?.description" class="text-xs text-muted-foreground/80 line-clamp-1 sm:line-clamp-2 max-w-2xl leading-relaxed">
              {{ detail.description }}
            </p>
          </div>
        </div>

        <!-- Stats & Actions -->
        <div class="flex items-center gap-6 sm:gap-8 shrink-0 ml-[4rem] sm:ml-0">
          <div class="flex items-center gap-4 sm:gap-6">
            <div class="flex flex-col items-center">
              <span class="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-1">总数</span>
              <span class="text-sm font-semibold font-mono text-foreground/80">{{ detail?.total_videos || 0 }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-1">解析</span>
              <span class="text-sm font-semibold font-mono text-foreground/80">{{ detail?.total_extract || 0 }}</span>
            </div>
          </div>

          <div v-if="canOpenRemote" class="flex rounded-lg border border-border/40 bg-muted/40 p-0.5">
            <button
              type="button"
              class="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors"
              :class="mode === 'local' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
              @click="emit('update:mode', 'local')"
            >
              <AppIcon name="library" class="h-3.5 w-3.5" />
              本地
            </button>
            <button
              type="button"
              class="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors"
              :class="mode === 'remote' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
              @click="emit('update:mode', 'remote')"
            >
              <AppIcon name="siteFallback" class="h-3.5 w-3.5" />
              远端
            </button>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="inline-flex h-8 w-8 items-center justify-center rounded-md border transition-colors"
              :class="detail?.is_special_followed ? 'border-amber-400/40 bg-amber-400/10 text-amber-600' : 'border-border/40 text-muted-foreground hover:bg-muted/60 hover:text-foreground'"
              :disabled="isTogglingSpecial"
              aria-label="切换特别关注"
              @click="handleToggleSpecialFollow"
            >
              <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': detail?.is_special_followed }" />
            </button>
            <div v-if="syncMessage" class="hidden max-w-40 truncate text-xs font-medium sm:block" :class="syncError ? 'text-destructive' : 'text-muted-foreground'">
              {{ syncMessage }}
            </div>
            <div class="flex overflow-hidden rounded-md border border-border/40 bg-background">
              <button
                type="button"
                class="inline-flex h-8 items-center gap-1.5 px-3 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="isSyncing"
                @click="handleDirectSync('incremental')"
              >
                <AppIcon name="refresh" class="h-3.5 w-3.5" :class="{ 'animate-spin': isSyncing }" />
                {{ isSyncing ? '同步中' : '同步' }}
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center border-l border-border/40 text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="isSyncing"
                    aria-label="选择同步模式"
                  >
                    <AppIcon name="chevronDown" class="h-3.5 w-3.5" />
                  </button>
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
          
          <button
            type="button"
            class="px-3 py-1.5 text-xs font-semibold rounded-md border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
            :disabled="isUnsubscribing"
            @click="handleUnsubscribe"
          >
            {{ isUnsubscribing ? '取消中...' : '取消订阅' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { getSubscriptionDetail, triggerDirectRefresh, unsubscribe as apiUnsubscribe, updateSpecialFollowStatus } from '@/api'
import { notifySubscriptionRemoved } from '@/utils/subscriptionEvents'

const props = defineProps({
  subscriptionId: { type: [String, Number], required: true },
  mode: { type: String, default: undefined }
})

const emit = defineEmits(['update:mode', 'loaded', 'synced'])

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
const isDesktop = window.desktopApp?.isDesktop === true

const canOpenRemote = computed(() => {
  return isDesktop && !!detail.value?.site && !!detail.value?.url
})

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const fetchDetail = async () => {
  if (!props.subscriptionId) return;
  loading.value = true;
  const { data, error } = await getSubscriptionDetail(props.subscriptionId);
  if (!error) {
    detail.value = data;
    emit('loaded', data)
  }
  loading.value = false;
};

const handleUnsubscribe = async () => {
  if (!props.subscriptionId || isUnsubscribing.value) return

  isUnsubscribing.value = true
  unsubscribeError.value = ''

  const { error } = await apiUnsubscribe(props.subscriptionId)

  if (error) {
    unsubscribeError.value = error?.message || '取消订阅失败'
    isUnsubscribing.value = false
    return
  }

  isVisible.value = false
  notifySubscriptionRemoved(props.subscriptionId)
  await wait(DISMISS_MS)
}

const handleToggleSpecialFollow = async () => {
  if (!props.subscriptionId || !detail.value || isTogglingSpecial.value) return

  isTogglingSpecial.value = true
  const nextValue = !detail.value.is_special_followed
  const { error } = await updateSpecialFollowStatus(props.subscriptionId, nextValue)
  if (!error) {
    detail.value = { ...detail.value, is_special_followed: nextValue }
    emit('loaded', detail.value)
  }
  isTogglingSpecial.value = false
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

  const { data, error } = await triggerDirectRefresh(props.subscriptionId, mode)

  if (error) {
    syncError.value = error?.message || '同步失败'
    syncMessage.value = syncError.value
    isSyncing.value = false
    return
  }

  syncMessage.value = buildSyncSuccessMessage(data, mode)
  await fetchDetail()
  emit('synced', data)
  isSyncing.value = false
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

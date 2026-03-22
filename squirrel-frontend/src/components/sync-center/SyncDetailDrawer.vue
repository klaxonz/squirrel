<template>
  <Sheet :open="open && !!item" @update:open="handleSheetToggle">
    <SheetContent side="right" class="w-full max-w-xl bg-background p-0">
      <div v-if="item" class="flex h-full flex-col">
        <div class="border-b border-border px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-3">
                <router-link :to="getSubscriptionLink(item.subscription_id)" class="shrink-0">
                  <img
                    :src="getAvatarSrc(item.subscription_avatar, `detail-drawer-${item.subscription_id}`)"
                    :alt="item.subscription_name"
                    class="h-12 w-12 rounded-full object-cover bg-card ring-1 ring-border"
                    referrerpolicy="no-referrer"
                    @error="(e) => handleAvatarError(e, `detail-drawer-${item?.subscription_id || 'unknown'}`)"
                  >
                </router-link>
                <div class="min-w-0">
                  <router-link
                    :to="getSubscriptionLink(item.subscription_id)"
                    class="text-lg font-semibold text-foreground truncate hover:text-primary"
                  >
                    {{ item.subscription_name }}
                  </router-link>
                  <div class="mt-2 flex items-center gap-2">
                    <Badge :variant="getStatusVariant(item.display_status)" class="rounded-full">
                      {{ getStatusLabel(item.display_status) }}
                    </Badge>
                    <Badge variant="outline" class="rounded-full">
                      {{ item.sync_mode === 'full' ? 'Full' : 'Incremental' }}
                    </Badge>
                    <span class="text-2xs text-muted-foreground">{{ item.site || 'unknown' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto space-y-6 px-6 py-6">
          <div class="grid grid-cols-2 gap-3">
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground/70">失败次数</p>
                <p class="mt-2 text-2xl font-semibold text-foreground">{{ item.failure_count || 0 }}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent class="p-4">
                <p class="text-2xs text-muted-foreground/70">待处理视频</p>
                <p class="mt-2 text-2xl font-semibold text-foreground">{{ item.pending_video_count || 0 }}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent class="p-5 space-y-4">
              <h3 class="text-sm font-medium text-foreground">时间信息</h3>
              <div class="grid grid-cols-1 gap-3">
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-muted-foreground/70">最后执行</span>
                  <span class="text-foreground">{{ item.last_sync_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-muted-foreground/70">最后成功</span>
                  <span class="text-foreground">{{ item.last_success_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-muted-foreground/70">排队时间</span>
                  <span class="text-foreground">{{ item.queued_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-muted-foreground/70">开始执行</span>
                  <span class="text-foreground">{{ item.locked_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-muted-foreground/70">下次执行</span>
                  <span class="text-foreground">{{ item.next_sync_at || '—' }}</span>
                </div>
                <div class="flex items-center justify-between gap-4 text-xs">
                  <span class="text-muted-foreground/70">最近更新时间</span>
                  <span class="text-foreground">{{ item.updated_at || '—' }}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-5">
              <h3 class="text-sm font-medium text-foreground">错误信息</h3>
              <pre class="mt-3 min-h-[7rem] whitespace-pre-wrap break-all rounded-xl border border-border bg-background p-4 text-xs text-muted-foreground">{{ item.last_error || '当前没有错误信息' }}</pre>
            </CardContent>
          </Card>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
          <Button as-child variant="outline" size="sm" class="rounded-full">
            <router-link :to="`/subscription/${item.subscription_id}/all`">打开订阅</router-link>
          </Button>
          <Button variant="secondary" size="sm" class="rounded-full" @click="emit('close')">关闭</Button>
          <Button :disabled="retrying" size="sm" class="rounded-full" @click="emit('retry')">
            <Loader2 v-if="retrying" class="h-4 w-4 animate-spin" />
            立即重试
          </Button>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useImageFallback } from '@/composables/useImageFallback'
import { Loader2 } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const props = defineProps<{
  item: SyncCenterItem | null
  open: boolean
  retrying: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'retry'): void
}>()

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()

const getSubscriptionLink = (subscriptionId: number) => `/subscription/${subscriptionId}/all`

const handleSheetToggle = (value: boolean) => {
  if (!value) {
    emit('close')
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'failed':
      return '失败'
    case 'running':
      return '运行中'
    case 'queued':
      return '排队中'
    case 'scheduled':
      return '即将执行'
    case 'deferred':
      return '已延后'
    default:
      return '正常'
  }
}

const getStatusVariant = (status: string) => {
  switch (status) {
    case 'failed':
      return 'destructive'
    case 'running':
    case 'queued':
      return 'default'
    case 'scheduled':
      return 'secondary'
    case 'deferred':
      return 'outline'
    default:
      return 'outline'
  }
}
</script>


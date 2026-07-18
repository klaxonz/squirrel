<template>
  <aside class="subscription-inspector" aria-label="频道详情">
    <header class="subscription-inspector__header">
      <SubscriptionAvatar
        :src="channel.avatar"
        :name="channel.name"
        size="lg"
        class="subscription-inspector__avatar"
      />
      <div class="subscription-inspector__identity">
        <h2>{{ channel.name }}</h2>
        <p>{{ channel.site || '未知来源' }}</p>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        title="关闭频道详情"
        aria-label="关闭频道详情"
        @click="$emit('close')"
      >
        <AppIcon name="close" class="h-4 w-4" />
      </Button>
    </header>

    <div class="subscription-inspector__body custom-scrollbar">
      <div class="subscription-inspector__actions">
        <Button
          variant="outline"
          size="sm"
          @click="$emit('open-detail')"
        >
          打开频道
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
        :loading="refreshing"
        @click="$emit('refresh')"
      >
          <AppIcon v-if="!refreshing" name="refresh" class="h-4 w-4" />
          立即同步
        </Button>
        <Button
          v-if="canOpenRemote"
          type="button"
          variant="ghost"
          size="sm"
          @click="$emit('open-remote')"
        >
          <AppIcon name="externalLink" class="h-4 w-4" />
          远端内容
        </Button>
      </div>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="subscription-inspector__special"
        :class="{ 'is-active': channel.is_special_followed }"
        :loading="togglingSpecial"
        :aria-pressed="channel.is_special_followed"
        @click="$emit('toggle-special')"
      >
        <AppIcon v-if="!togglingSpecial" name="star" class="h-4 w-4" />
        {{ channel.is_special_followed ? '已设为特别关注' : '设为特别关注' }}
      </Button>

      <dl class="subscription-inspector__metrics">
        <div>
          <dt>视频</dt>
          <dd class="app-mono">{{ channel.total_videos }}</dd>
        </div>
        <div>
          <dt>未读</dt>
          <dd class="app-mono">{{ channel.unread_count }}</dd>
        </div>
        <div>
          <dt>待处理</dt>
          <dd class="app-mono">{{ channel.pending_video_count }}</dd>
        </div>
      </dl>

      <section class="subscription-inspector__section">
        <div class="subscription-inspector__section-heading">
          <h3>同步状态</h3>
          <span :class="statusClass">{{ statusLabel }}</span>
        </div>
        <dl class="subscription-inspector__details">
          <div>
            <dt>最近成功</dt>
            <dd>{{ formatDate(channel.last_success_at) }}</dd>
          </div>
          <div>
            <dt>下次同步</dt>
            <dd>{{ formatDate(channel.next_sync_at) }}</dd>
          </div>
        </dl>
        <p v-if="channel.last_error" class="subscription-inspector__error">
          {{ channel.last_error }}
        </p>
      </section>

      <section v-if="channel.description" class="subscription-inspector__section">
        <h3>频道简介</h3>
        <p class="subscription-inspector__description">{{ channel.description }}</p>
      </section>

      <section class="subscription-inspector__section">
        <div class="subscription-inspector__section-heading">
          <h3>最近内容</h3>
          <span>{{ channel.recent_videos.length }}</span>
        </div>
        <div v-if="channel.recent_videos.length" class="subscription-inspector__recent">
          <Button
            v-for="video in channel.recent_videos"
            :key="video.id"
            unstyled
            type="button"
            class="subscription-inspector__recent-item"
            @click="$emit('open-video', video.id)"
          >
            <span>{{ video.title }}</span>
            <small>{{ formatDate(video.publish_date) }}</small>
          </Button>
        </div>
        <p v-else class="subscription-inspector__muted">暂无最近内容</p>
      </section>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { formatDate } from '@/shared/lib/dateFormat'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import {
  isSubscriptionSyncBusy,
  isSubscriptionSyncFailed,
} from '@/features/video/lib/subscriptionPresenters'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

const props = defineProps<{
  channel: SubscriptionListItem
  canOpenRemote: boolean
  refreshing: boolean
  togglingSpecial: boolean
}>()

defineEmits<{
  close: []
  refresh: []
  'open-detail': []
  'open-remote': []
  'toggle-special': []
  'open-video': [videoId: number]
}>()

const statusLabel = computed(() => {
  if (isSubscriptionSyncFailed(props.channel)) return '同步失败'
  if (isSubscriptionSyncBusy(props.channel)) {
    return props.channel.sync_status === 'queued' ? '等待同步' : '同步中'
  }
  if (props.channel.pending_video_count > 0) return '处理中'
  return '正常'
})

const statusClass = computed(() => ({
  'subscription-inspector__status': true,
  'is-error': isSubscriptionSyncFailed(props.channel),
  'is-busy': isSubscriptionSyncBusy(props.channel) || props.channel.pending_video_count > 0,
}))
</script>

<style scoped>
.subscription-inspector {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: calc(var(--z-content) + 1);
  display: flex;
  width: 22rem;
  min-height: 0;
  flex-direction: column;
  border-left: 1px solid var(--app-hairline);
  background: hsl(var(--background));
  box-shadow: var(--app-panel-shadow);
}

.subscription-inspector__header {
  display: flex;
  min-height: 4.5rem;
  flex: none;
  align-items: center;
  gap: var(--space-3);
  border-bottom: 1px solid var(--app-hairline);
  padding: var(--space-3) var(--space-4);
}

.subscription-inspector__avatar {
  flex: none;
}

.subscription-inspector__identity {
  min-width: 0;
  flex: 1 1 auto;
}

.subscription-inspector__identity h2 {
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-inspector__identity p {
  margin-top: 0.2rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 500;
}

.subscription-inspector__body {
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  padding: var(--space-4);
}

.subscription-inspector__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.subscription-inspector__special {
  width: 100%;
  justify-content: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-3);
  color: hsl(var(--muted-foreground));
}

.subscription-inspector__special.is-active {
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--muted-foreground) / 0.86);
}

.subscription-inspector__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: var(--space-5);
  border-top: 1px solid var(--app-hairline);
  border-bottom: 1px solid var(--app-hairline);
}

.subscription-inspector__metrics > div {
  padding: var(--space-3) 0;
}

.subscription-inspector__metrics > div + div {
  border-left: 1px solid var(--app-hairline);
  padding-left: var(--space-3);
}

.subscription-inspector__metrics dt,
.subscription-inspector__details dt {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: var(--app-text-badge-size);
  font-weight: 600;
}

.subscription-inspector__metrics dd {
  margin-top: 0.25rem;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 650;
}

.subscription-inspector__section {
  padding: var(--space-5) 0;
  border-bottom: 1px solid var(--app-hairline);
}

.subscription-inspector__section > h3,
.subscription-inspector__section-heading h3 {
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 650;
}

.subscription-inspector__section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.subscription-inspector__section-heading > span {
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: var(--app-text-badge-size);
  font-weight: 600;
}

.subscription-inspector__status.is-error {
  color: hsl(var(--destructive));
}

.subscription-inspector__status.is-busy {
  color: hsl(var(--warning));
}

.subscription-inspector__details {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.subscription-inspector__details > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.subscription-inspector__details dd {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 500;
  text-align: right;
}

.subscription-inspector__error {
  margin-top: var(--space-3);
  border: 1px solid hsl(var(--destructive) / 0.2);
  border-radius: var(--radius-md);
  background: hsl(var(--destructive) / 0.06);
  padding: var(--space-3);
  color: hsl(var(--destructive));
  font-size: 0.6875rem;
  line-height: 1.5;
}

.subscription-inspector__description {
  margin-top: var(--space-3);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.6;
}

.subscription-inspector__recent {
  display: grid;
  margin-top: var(--space-2);
}

.subscription-inspector__recent-item {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  border-radius: var(--radius-md);
  padding: 0.625rem;
  text-align: left;
  cursor: pointer;
}

.subscription-inspector__recent-item:hover,
.subscription-inspector__recent-item:focus-visible {
  background: hsl(var(--muted) / 0.45);
  outline: none;
}

.subscription-inspector__recent-item span {
  overflow: hidden;
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.75rem;
  font-weight: 550;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-inspector__recent-item small,
.subscription-inspector__muted {
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: var(--app-text-badge-size);
  font-weight: 500;
}

.subscription-inspector__muted {
  margin-top: var(--space-3);
}
</style>

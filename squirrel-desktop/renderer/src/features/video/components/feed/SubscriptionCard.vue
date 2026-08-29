<template>
  <article
    class="subscription-row"
    :class="{
      'subscription-row--error': syncFailed,
      'subscription-row--selected': selected,
    }"
  >
    <button

      type="button"
      class="subscription-row__identity"
      :title="cardTitle"
      @click="$emit('click')"
    >
      <SubscriptionAvatar
        :src="subscription.avatar"
        :name="subscription.name"
        size="md"
        class="subscription-row__avatar"
      />

      <span class="subscription-row__copy">
        <span class="subscription-row__title-line">
          <strong class="subscription-row__title">{{ subscription.name }}</strong>
          <span v-if="subscription.is_nsfw" class="subscription-row__nsfw">18+</span>
        </span>
        <span v-if="subscription.site" class="subscription-row__site">{{ subscription.site }}</span>
      </span>
    </button>

    <span class="subscription-row__metric app-mono">{{ subscription.total_videos }}</span>

    <span
      class="subscription-row__metric app-mono"
      :class="{ 'subscription-row__metric--active': subscription.unread_count > 0 }"
      :title="`${subscription.unread_count} 个未读`"
    >
      {{ unreadLabel || 0 }}
    </span>

    <span
      class="subscription-row__updated"
      :title="subscription.last_success_at || '尚未同步'"
    >
      {{ lastUpdatedText }}
    </span>

    <span
      v-if="syncFailed"
      class="subscription-row__state subscription-row__state--error"
      :title="errorLabel"
    >
      <AppIcon name="warning" class="h-3 w-3" />
      同步失败
    </span>
    <span v-else-if="syncBusy" class="subscription-row__state">
      <AppSpinner size="sm" />
      {{ syncLabel }}
    </span>
    <span
      v-else-if="subscription.pending_video_count > 0"
      class="subscription-row__state subscription-row__state--pending"
    >
      <AppIcon name="time" class="h-3 w-3" />
      {{ subscription.pending_video_count }} 待处理
    </span>
    <span v-else class="subscription-row__state subscription-row__state--healthy">
      <span class="subscription-row__state-dot" />
      正常
    </span>

    <Button
      type="button"
      text severity="secondary"
      size="sm" icon-only
      class="subscription-row__star"
      :class="{ 'is-active': subscription.is_special_followed }"
      :disabled="toggling"
      :aria-pressed="subscription.is_special_followed"
      :aria-label="subscription.is_special_followed ? '取消特别关注' : '设为特别关注'"
      @click="$emit('toggleSpecial', subscription)"
    >
      <AppSpinner v-if="toggling" size="sm" />
      <AppIcon
        v-else
        name="star"
        class="h-3.5 w-3.5"
      />
    </Button>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import { formatDate } from '@/shared/lib/dateFormat'
import {
  formatUnreadCount,
  isSubscriptionSyncBusy,
  isSubscriptionSyncFailed,
  subscriptionSyncErrorLabel,
} from '@/features/video/lib/subscriptionPresenters'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

const props = defineProps<{
  subscription: SubscriptionListItem
  toggling?: boolean
  selected?: boolean
}>()

defineEmits<{
  click: []
  toggleSpecial: [subscription: SubscriptionListItem]
}>()

const unreadLabel = computed(() => formatUnreadCount(props.subscription.unread_count))
const syncFailed = computed(() => isSubscriptionSyncFailed(props.subscription))
const syncBusy = computed(() => isSubscriptionSyncBusy(props.subscription))
const errorLabel = computed(() => subscriptionSyncErrorLabel(props.subscription) || '同步失败')
const syncLabel = computed(() => props.subscription.sync_status === 'queued' ? '等待同步' : '同步中')
const lastUpdatedText = computed(() => (
  props.subscription.last_success_at
    ? formatDate(props.subscription.last_success_at)
    : '尚未同步'
))

const cardTitle = computed(() => {
  const parts = [props.subscription.name]
  if (props.subscription.site) parts.push(props.subscription.site)
  parts.push(`${props.subscription.total_videos} 个视频`)
  if (props.subscription.unread_count > 0) parts.push(`${props.subscription.unread_count} 个未读`)
  if (syncFailed.value) parts.push(errorLabel.value)
  return parts.join(' · ')
})
</script>

<style scoped>
.subscription-row {
  display: grid;
  min-width: 0;
  min-height: 4rem;
  grid-template-columns: var(
    --subscription-table-columns,
    minmax(15rem, 1fr) 5.5rem 5.5rem 8rem minmax(6.5rem, 8rem) 1.75rem
  );
  align-items: center;
  gap: 1rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.625rem 0.75rem;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.subscription-row:hover,
.subscription-row:focus-within {
  background: hsl(var(--foreground) / 0.025);
}

.subscription-row--error {
  background: hsl(var(--destructive) / 0.025);
}

.subscription-row--selected {
  background: hsl(var(--foreground) / 0.045);
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.08);
}

.subscription-row__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.75rem;
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.subscription-row__identity:focus-visible {
  border-radius: var(--radius-sm);
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.subscription-row__identity:active {
  transform: translateY(1px);
}

.subscription-row__avatar {
  flex: none;
  box-shadow: 0 0 0 1px var(--app-surface-border-subtle);
}

.subscription-row__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.15rem;
}

.subscription-row__title-line {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.4rem;
}

.subscription-row__title {
  min-width: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: var(--app-text-md);
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-row__nsfw {
  flex: none;
  color: hsl(var(--destructive));
  font-size: var(--app-text-badge-size);
  font-weight: 700;
  line-height: 1;
}

.subscription-row__site {
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: var(--app-text-xs);
  font-weight: 500;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-row__metric {
  justify-self: end;
  color: hsl(var(--muted-foreground) / 0.88);
  font-size: var(--app-text-sm);
  font-weight: 550;
  white-space: nowrap;
}

.subscription-row__metric--active {
  color: hsl(var(--foreground) / 0.82);
}

.subscription-row__updated {
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: var(--app-text-xs);
  font-weight: 500;
  white-space: nowrap;
}

.subscription-row__state {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.3rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: var(--app-text-xs);
  font-weight: 550;
  white-space: nowrap;
}

.subscription-row__state--error {
  color: hsl(var(--destructive));
}

.subscription-row__state--pending {
  color: hsl(var(--warning));
}

.subscription-row__state--healthy {
  color: hsl(var(--muted-foreground) / 0.72);
}

.subscription-row__state-dot {
  width: 0.375rem;
  height: 0.375rem;
  flex: none;
  border-radius: 999px;
  background: hsl(var(--success) / 0.8);
}

.subscription-row__star {
  opacity: 0;
  color: hsl(var(--muted-foreground) / 0.55);
}

.subscription-row__star.is-active {
  opacity: 0.56;
  color: hsl(var(--muted-foreground) / 0.78);
}

.subscription-row:hover .subscription-row__star,
.subscription-row:focus-within .subscription-row__star {
  opacity: 0.78;
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .subscription-row__star {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .subscription-row {
    transition: none;
  }

  .subscription-row__identity:active {
    transform: none;
  }
}
</style>

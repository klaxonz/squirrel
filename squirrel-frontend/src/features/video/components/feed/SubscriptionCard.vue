<template>
  <div
    class="subscription-card group"
    role="button"
    tabindex="0"
    @click="$emit('click')"
    @keydown.enter.prevent="$emit('click')"
    @keydown.space.prevent="$emit('click')"
  >
    <!-- Media first: always reserve a 3-up strip so the grid rhythm stays calm. -->
    <div class="subscription-card__media" aria-hidden="true">
      <div
        v-for="(slot, index) in previewSlots"
        :key="slot?.id ?? `empty-${index}`"
        class="subscription-card__thumb"
      >
        <VideoThumbnail
          v-if="slot?.thumbnail"
          :src="slot.thumbnail"
          fit="cover"
          img-class="subscription-card__thumb-img"
        />
      </div>
    </div>

    <div class="subscription-card__body">
      <div class="subscription-card__identity">
        <SubscriptionAvatar
          :src="subscription.avatar"
          :name="subscription.name"
          size="md"
          class="subscription-card__avatar"
        />

        <div class="subscription-card__copy min-w-0 flex-1">
          <div class="subscription-card__title-row">
            <h3 class="subscription-card__title">{{ subscription.name }}</h3>
            <Button
              type="button"
              variant="ghost"
              size="mini-icon"
              class="subscription-card__star"
              :class="{ 'is-active': subscription.is_special_followed }"
              :disabled="toggling"
              :aria-pressed="subscription.is_special_followed"
              aria-label="切换特别关注"
              @click.stop="$emit('toggleSpecial', subscription)"
            >
              <AppSpinner v-if="toggling" size="sm" />
              <AppIcon
                v-else
                name="star"
                class="h-3.5 w-3.5"
                :class="{ 'fill-current': subscription.is_special_followed }"
              />
            </Button>
          </div>

          <div class="subscription-card__meta">
            <span v-if="subscription.site" class="subscription-card__site">{{ subscription.site }}</span>
            <span v-if="subscription.site" class="subscription-card__dot" aria-hidden="true">·</span>
            <span class="app-mono">{{ subscription.total_videos || 0 }}</span>
            <span class="subscription-card__meta-label">视频</span>
            <template v-if="unreadLabel">
              <span class="subscription-card__dot" aria-hidden="true">·</span>
              <span class="subscription-card__unread app-mono" :title="`${subscription.unread_count} 个未读`">
                {{ unreadLabel }}
              </span>
              <span class="subscription-card__meta-label">未读</span>
            </template>
            <template v-if="syncFailed">
              <span class="subscription-card__dot" aria-hidden="true">·</span>
              <span class="subscription-card__status subscription-card__status--error" :title="errorLabel">
                <AppIcon name="warning" class="h-3 w-3" />
                异常
              </span>
            </template>
            <template v-else-if="syncBusy">
              <span class="subscription-card__dot" aria-hidden="true">·</span>
              <span class="subscription-card__status">同步中</span>
            </template>
            <span v-if="subscription.is_nsfw" class="subscription-card__nsfw">18+</span>
          </div>
        </div>
      </div>

      <div class="subscription-card__footer">
        <span class="subscription-card__time">{{ lastUpdatedText }}</span>
        <span v-if="subscription.pending_video_count > 0" class="subscription-card__pending app-mono">
          {{ subscription.pending_video_count }} 待处理
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { formatDate } from '@/shared/lib/dateFormat'
import {
  formatUnreadCount,
  getSubscriptionRecentVideos,
  isSubscriptionSyncBusy,
  isSubscriptionSyncFailed,
  subscriptionSyncErrorLabel,
} from '@/features/video/lib/subscriptionPresenters'
import type { SubscriptionListItem, SubscriptionRecentVideo } from '@/features/video/types/subscription'

const props = defineProps<{
  subscription: SubscriptionListItem
  toggling?: boolean
}>()

defineEmits(['click', 'toggleSpecial'])

const previewVideos = computed(() => getSubscriptionRecentVideos(props.subscription).slice(0, 3))
const previewSlots = computed(() => {
  const slots: Array<SubscriptionRecentVideo | null> = [...previewVideos.value]
  while (slots.length < 3) slots.push(null)
  return slots
})

const unreadLabel = computed(() => formatUnreadCount(props.subscription.unread_count))
const syncFailed = computed(() => isSubscriptionSyncFailed(props.subscription))
const syncBusy = computed(() => isSubscriptionSyncBusy(props.subscription))
const errorLabel = computed(() => subscriptionSyncErrorLabel(props.subscription) || '同步失败')

const lastUpdatedText = computed(() => {
  const date = props.subscription.updated_at
    || props.subscription.last_published_at
    || props.subscription.last_success_at
  return date ? formatDate(date) : '尚未更新'
})
</script>

<style scoped>
.subscription-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-card-radius);
  background: hsl(var(--card));
  cursor: pointer;
  transition:
    border-color var(--duration-base) var(--ease-default),
    box-shadow var(--duration-base) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.subscription-card:hover {
  border-color: hsl(var(--border) / 0.8);
  box-shadow:
    0 1px 2px hsl(0 0% 0% / 0.08),
    0 10px 24px hsl(0 0% 0% / 0.14);
}

.subscription-card:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.subscription-card:active {
  transform: scale(0.995);
}

.subscription-card__media {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  background: hsl(0 0% 0% / 0.55);
  isolation: isolate;
}

.subscription-card__thumb {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: hsl(0 0% 0% / 0.72);
}

.subscription-card__thumb :deep(img),
.subscription-card__thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-base) var(--ease-default), filter var(--duration-fast) var(--ease-default);
}

.subscription-card:hover .subscription-card__thumb :deep(img),
.subscription-card:hover .subscription-card__thumb-img {
  transform: scale(1.03);
  filter: brightness(1.06);
}

.subscription-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: 0.75rem 0.875rem 0.75rem;
}

.subscription-card__identity {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
}

.subscription-card__avatar {
  margin-top: 0.125rem;
  box-shadow: 0 0 0 1px var(--app-surface-border-subtle);
}

.subscription-card__copy {
  min-width: 0;
}

.subscription-card__title-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.subscription-card__title {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground) / 0.94);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--duration-fast) var(--ease-default);
}

.subscription-card:hover .subscription-card__title {
  color: hsl(var(--primary));
}

.subscription-card__star {
  flex: 0 0 auto;
  margin-top: -0.125rem;
  color: hsl(var(--muted-foreground) / 0.55);
}

.subscription-card__star.is-active {
  color: hsl(var(--warning));
}

.subscription-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.35rem;
  margin-top: 0.2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.35;
}

.subscription-card__site {
  max-width: 6.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-transform: lowercase;
}

.subscription-card__dot {
  color: hsl(var(--muted-foreground) / 0.55);
}

.subscription-card__meta-label {
  color: hsl(var(--muted-foreground) / 0.85);
}

.subscription-card__unread {
  color: hsl(var(--primary));
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.subscription-card__status {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  color: hsl(var(--muted-foreground));
}

.subscription-card__status--error {
  color: hsl(var(--destructive) / 0.92);
}

.subscription-card__nsfw {
  margin-left: 0.15rem;
  padding: 0.05rem 0.35rem;
  border: 1px solid hsl(var(--destructive) / 0.35);
  border-radius: var(--radius-sm);
  color: hsl(var(--destructive));
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.2;
}

.subscription-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding-top: 0.125rem;
}

.subscription-card__time,
.subscription-card__pending {
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.6875rem;
  font-weight: 500;
}

.subscription-card__pending {
  font-variant-numeric: tabular-nums;
}

@media (prefers-reduced-motion: reduce) {
  .subscription-card,
  .subscription-card__title,
  .subscription-card__thumb :deep(img),
  .subscription-card__thumb-img {
    transition: none;
  }

  .subscription-card:active {
    transform: none;
  }

  .subscription-card:hover .subscription-card__thumb :deep(img),
  .subscription-card:hover .subscription-card__thumb-img {
    transform: none;
    filter: none;
  }
}
</style>

<template>
  <div class="app-media-header" :class="rootClass">
    <div class="app-media-header__inner channel-identity">
      <div
        v-if="loading && !hasIdentity"
        class="channel-identity__body channel-identity__body--skeleton"
        role="status"
        :aria-label="loadingLabel"
      >
        <AppSkeleton width="3.5rem" height="3.5rem" rounded="var(--radius-pill)" />
        <div class="channel-identity__skeleton-copy">
          <AppSkeleton width="12rem" height="1.375rem" />
          <AppSkeleton width="min(20rem, 52vw)" height="0.875rem" />
          <AppSkeleton width="9rem" height="0.75rem" />
        </div>
      </div>

      <div v-else-if="hasIdentity" class="channel-identity__body">
        <a
          v-if="url"
          :href="url"
          target="_blank"
          rel="noopener noreferrer"
          class="channel-identity__avatar"
        >
          <SubscriptionAvatar :src="avatar" :name="displayName" size="full" />
        </a>
        <div v-else class="channel-identity__avatar">
          <SubscriptionAvatar :src="avatar" :name="displayName" size="full" />
        </div>

        <div class="channel-identity__copy">
          <div class="channel-identity__title-row">
            <a
              v-if="url"
              :href="url"
              target="_blank"
              rel="noopener noreferrer"
              class="channel-identity__name-link"
            >
              <h1 class="channel-identity__name">{{ displayName }}</h1>
            </a>
            <h1 v-else class="channel-identity__name">{{ displayName }}</h1>
            <slot name="badges">
              <span v-if="badge" class="channel-identity__badge">{{ badge }}</span>
            </slot>
          </div>

          <p v-if="description" class="channel-identity__desc">{{ description }}</p>

          <div v-if="$slots.stats" class="channel-identity__stats">
            <slot name="stats" />
          </div>
        </div>
      </div>

      <div v-else-if="error" class="channel-identity__body channel-identity__body--error" role="alert">
        <AppIcon name="warning" class="channel-identity__error-icon" />
        <div class="channel-identity__error-copy">
          <strong>{{ errorTitle }}</strong>
          <p>{{ error }}</p>
        </div>
        <Button type="button" variant="outline" size="sm" :disabled="loading" @click="emit('retry')">
          重试
        </Button>
      </div>

      <div v-if="$slots.actions" class="channel-identity__actions">
        <slot name="actions" />
      </div>
    </div>

    <slot name="footer" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import { Skeleton as AppSkeleton } from '@/shared/ui/skeleton'
import { Button } from '@/shared/ui/button'

/**
 * One identity header for creators, subscriptions and remote channels: avatar,
 * name, optional badge/description, a stats slot, and an actions slot that
 * stays on the same baseline. Callers own their data fetching and actions.
 */
const props = withDefaults(defineProps<{
  name?: string | null
  avatar?: string | null
  url?: string | null
  description?: string | null
  badge?: string | null
  loading?: boolean
  error?: string
  errorTitle?: string
  loadingLabel?: string
  nameFallback?: string
  rootClass?: string
}>(), {
  name: '',
  avatar: null,
  url: null,
  description: null,
  badge: null,
  loading: false,
  error: '',
  errorTitle: '信息加载失败',
  loadingLabel: '正在加载信息',
  nameFallback: '未知名称',
  rootClass: '',
})

const emit = defineEmits<{ retry: [] }>()

const displayName = computed(() => props.name?.trim() || props.nameFallback)
// A refresh failure must not replace an identity that is already on screen.
const hasIdentity = computed(() => Boolean(props.name?.trim()))
</script>

<style scoped>
.channel-identity {
  max-width: var(--app-content-media-max);
  padding-inline: var(--app-content-media-gutter);
  padding-block: clamp(1.25rem, 2.2vw, 1.75rem);
}

.channel-identity__body {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  gap: clamp(0.875rem, 1.6vw, 1.125rem);
}

.channel-identity__body--skeleton {
  align-items: flex-start;
}

.channel-identity__avatar {
  display: block;
  width: 3.5rem;
  height: 3.5rem;
  flex: 0 0 auto;
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: hsl(var(--muted));
  box-shadow: 0 0 0 1px var(--app-surface-border);
}

.channel-identity__copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.3rem;
}

.channel-identity__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
}

.channel-identity__name {
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-family: var(--font-display);
  font-size: var(--app-text-2xl);
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.channel-identity__name-link {
  min-width: 0;
  color: inherit;
  text-decoration: none;
}

.channel-identity__name-link:hover .channel-identity__name {
  text-decoration: underline;
  text-underline-offset: 0.15em;
}

.channel-identity__badge {
  display: inline-flex;
  height: 1.25rem;
  flex: none;
  align-items: center;
  border: 1px solid var(--app-surface-border);
  border-radius: var(--radius-sm);
  padding: 0 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 600;
}

.channel-identity__desc {
  display: -webkit-box;
  overflow: hidden;
  max-width: 44rem;
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  line-height: 1.55;
  text-wrap: pretty;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.channel-identity__stats {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 1.125rem;
  margin-top: 0.15rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.channel-identity__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

.channel-identity__skeleton-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.15rem;
}

.channel-identity__body--error {
  align-items: center;
  color: hsl(var(--destructive));
}

.channel-identity__error-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex: none;
}

.channel-identity__error-copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.15rem;
}

.channel-identity__error-copy strong {
  font-size: var(--app-text-base);
  font-weight: 600;
}

.channel-identity__error-copy p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  line-height: 1.5;
}

@media (max-width: 900px) {
  .app-media-header__inner {
    flex-direction: column;
    align-items: stretch;
  }

  .channel-identity__actions {
    justify-content: flex-start;
  }
}
</style>

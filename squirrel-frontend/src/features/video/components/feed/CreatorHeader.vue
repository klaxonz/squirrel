<template>
  <div class="app-media-header">
    <div class="app-media-header__inner creator-header__inner">
      <div class="creator-header__identity">
        <a
          v-if="detail?.url"
          :href="detail.url"
          target="_blank"
          rel="noopener noreferrer"
          class="creator-header__avatar"
        >
          <SubscriptionAvatar
            :src="detail?.avatar || null"
            :name="detail?.name || '未知创作者'"
            size="full"
          />
        </a>
        <div v-else class="creator-header__avatar">
          <SubscriptionAvatar
            :src="detail?.avatar || null"
            :name="detail?.name || '未知创作者'"
            size="full"
          />
        </div>

        <div class="creator-header__copy">
          <div class="creator-header__title-row">
            <a
              v-if="detail?.url"
              :href="detail.url"
              target="_blank"
              rel="noopener noreferrer"
              class="creator-header__name-link"
            >
              <h1 class="app-h2 truncate">{{ detail?.name || '未知创作者' }}</h1>
            </a>
            <h1 v-else class="app-h2 truncate">{{ detail?.name || '未知创作者' }}</h1>
          </div>

          <p v-if="detail?.description" class="creator-header__desc">
            {{ detail.description }}
          </p>

          <div class="creator-header__stats">
            <span class="creator-header__stat">
              <span class="creator-header__stat-label">视频</span>
              <span class="creator-header__stat-value">{{ detail?.total_videos ?? 0 }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import { getCreatorDetail } from '@/shared/api'
import type { CreatorDetail } from '@/features/video/types/creator'

const props = defineProps<{
  creatorId: string | number
}>()

const emit = defineEmits<{
  loaded: [detail: CreatorDetail]
  error: [message: string]
}>()

const detail = ref<CreatorDetail | null>(null)

const fetchDetail = async () => {
  if (!props.creatorId) return
  try {
    const data = await getCreatorDetail(props.creatorId)
    detail.value = data
    emit('loaded', data)
  } catch {
    emit('error', '创作者信息加载失败')
  }
}

watch(() => props.creatorId, () => {
  detail.value = null
  fetchDetail()
}, { immediate: true })
</script>

<style scoped>
.creator-header__inner {
  --app-page-max-width: 2400px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.creator-header__identity {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: flex-start;
  gap: var(--space-4);
}

.creator-header__avatar {
  flex: 0 0 auto;
  width: 5.5rem;
  height: 5.5rem;
  overflow: hidden;
  border-radius: 999px;
}

.creator-header__copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 0.5rem;
}

.creator-header__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
}

.creator-header__name-link {
  min-width: 0;
  color: inherit;
  text-decoration: none;
}

.creator-header__name-link:hover {
  text-decoration: underline;
  text-underline-offset: 0.15em;
}

.creator-header__desc {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.creator-header__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
}

.creator-header__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
}

.creator-header__stat-label {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.creator-header__stat-value {
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
</style>

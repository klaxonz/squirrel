<template>
  <div class="app-media-header">
    <div class="app-media-header__inner creator-header__inner">
      <div v-if="loading && !detail" class="creator-header__identity creator-header__skeleton" aria-label="创作者信息加载中" role="status">
        <AppSkeleton width="3.5rem" height="3.5rem" radius="var(--app-surface-radius)" />
        <div class="creator-header__skeleton-copy">
          <AppSkeleton width="12rem" height="1.5rem" />
          <AppSkeleton width="20rem" height="0.875rem" />
          <AppSkeleton width="8rem" height="0.75rem" />
        </div>
      </div>

      <div v-else-if="detail" class="creator-header__identity">
        <a v-if="detail.url" :href="detail.url" target="_blank" rel="noopener noreferrer" class="creator-header__avatar">
          <SubscriptionAvatar :src="detail.avatar || null" :name="detail.name || '未知创作者'" size="full" />
        </a>
        <div v-else class="creator-header__avatar">
          <SubscriptionAvatar :src="detail.avatar || null" :name="detail.name || '未知创作者'" size="full" />
        </div>

        <div class="creator-header__copy">
          <div class="creator-header__title-row">
            <a v-if="detail.url" :href="detail.url" target="_blank" rel="noopener noreferrer" class="creator-header__name-link">
              <h1 class="app-h2 truncate">{{ detail.name || '未知创作者' }}</h1>
            </a>
            <h1 v-else class="app-h2 truncate">{{ detail.name || '未知创作者' }}</h1>
            <span v-if="detail.is_deleted" class="creator-header__badge">已停用</span>
          </div>

          <p v-if="detail.description" class="creator-header__desc">{{ detail.description }}</p>

          <div class="creator-header__stats">
            <span class="creator-header__stat">
              <span class="creator-header__stat-label">视频</span>
              <span class="creator-header__stat-value">{{ detail.total_videos ?? 0 }}</span>
            </span>
            <span v-if="sourceLabel" class="creator-header__stat">
              <span class="creator-header__stat-label">来源</span>
              <span class="creator-header__stat-value creator-header__stat-value--text">{{ sourceLabel }}</span>
            </span>
            <a v-if="detail.url" :href="detail.url" target="_blank" rel="noopener noreferrer" class="creator-header__site-link">
              访问主页 <AppIcon name="externalLink" class="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>

      <div v-else class="creator-header__identity creator-header__identity--error" role="alert">
        <AppIcon name="warning" class="h-5 w-5" />
        <div>
          <strong>创作者信息加载失败</strong>
          <p>{{ detailError }}</p>
        </div>
        <Button type="button" severity="secondary" outlined size="sm" :disabled="loading" @click="fetchDetail">重试</Button>
      </div>

      <span v-if="loading && detail" class="creator-header__refreshing" role="status">正在更新创作者信息</span>
      <Button v-if="detail && detailError" type="button" severity="secondary" outlined size="sm" @click="fetchDetail">重试信息加载</Button>
    </div>

    <div v-if="detail && detailError" class="creator-header__refresh-error" role="alert">
      <AppIcon name="warning" class="h-4 w-4" />
      <span>{{ detailError }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import { Button } from '@/shared/ui/button'
import { getCreatorDetail } from '@/shared/api'
import { errorMessage } from '@/shared/lib/errorMessage'
import type { CreatorDetail } from '@/features/video/types/creator'

const props = defineProps<{
  creatorId: string | number
}>()

const emit = defineEmits<{
  loaded: [detail: CreatorDetail]
  error: [message: string]
  'state-change': [state: { loading: boolean; error: string }]
}>()

const detail = ref<CreatorDetail | null>(null)
const loading = ref(false)
const detailError = ref('')

const parsedExtraData = computed<Record<string, unknown>>(() => {
  const extra = detail.value?.extra_data
  if (extra && typeof extra === 'object') return extra
  if (typeof extra !== 'string') return {}
  try {
    const parsed = JSON.parse(extra)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
})

const sourceLabel = computed(() => {
  const extra = parsedExtraData.value
  const explicit = extra.site_name || extra.site || extra.source_name || extra.source
  if (typeof explicit === 'string' && explicit.trim()) return explicit.trim()
  try {
    return detail.value?.url ? new URL(detail.value.url).hostname.replace(/^www\./, '') : ''
  } catch {
    return ''
  }
})

let detailRequestToken = 0
const fetchDetail = async () => {
  if (!props.creatorId) return
  const requestToken = ++detailRequestToken
  loading.value = true
  detailError.value = ''
  emit('state-change', { loading: true, error: '' })
  try {
    const data = await getCreatorDetail(props.creatorId)
    if (requestToken !== detailRequestToken) return
    detail.value = data
    emit('loaded', data)
  } catch (err) {
    if (requestToken !== detailRequestToken) return
    detailError.value = errorMessage(err, '创作者信息加载失败')
    emit('error', detailError.value)
  } finally {
    if (requestToken === detailRequestToken) {
      loading.value = false
      emit('state-change', { loading: false, error: detailError.value })
    }
  }
}

watch(() => props.creatorId, () => {
  detailRequestToken += 1
  detail.value = null
  detailError.value = ''
  fetchDetail()
}, { immediate: true })

defineExpose({ refresh: fetchDetail })
</script>

<style scoped>
.creator-header__inner {
  --app-page-max-width: var(--app-content-media-max);
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

.creator-header__skeleton-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.125rem;
}

.creator-header__identity--error {
  align-items: center;
  color: hsl(var(--destructive));
}

.creator-header__identity--error p {
  margin: 0.125rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
}

.creator-header__avatar {
  flex: 0 0 auto;
  width: 3.5rem;
  height: 3.5rem;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--muted));
}

.creator-header__copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 0.375rem;
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
  transition: color var(--duration-fast) var(--ease-default);
}

.creator-header__name-link:hover {
  text-decoration: underline;
  text-underline-offset: 0.15em;
}

.creator-header__badge {
  flex: none;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.125rem 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 650;
}

.creator-header__desc {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-base);
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
  font-size: var(--app-text-sm);
}

.creator-header__stat-value {
  color: hsl(var(--foreground));
  font-size: var(--app-text-base);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.creator-header__stat-value--text {
  font-family: inherit;
  font-size: var(--app-text-md);
}

.creator-header__site-link {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-default);
}

.creator-header__site-link:hover {
  color: hsl(var(--foreground));
}

.creator-header__refreshing {
  flex: none;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.creator-header__refresh-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: min(var(--app-content-media-max), 100%);
  margin: 0 auto;
  padding: 0.5rem var(--app-page-gutter);
  border-top: 1px solid hsl(var(--destructive) / 0.2);
  color: hsl(var(--destructive));
  font-size: var(--app-text-md);
}
</style>

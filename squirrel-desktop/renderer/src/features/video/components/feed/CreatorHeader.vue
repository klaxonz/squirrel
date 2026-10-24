<template>
  <ChannelIdentityHeader
    :loading="loading"
    :name="detail?.name"
    :avatar="detail?.avatar"
    :url="detail?.url"
    :description="detail?.description"
    :badge="detail?.is_deleted ? '已停用' : null"
    :error="detailError"
    error-title="创作者信息加载失败"
    loading-label="创作者信息加载中"
    name-fallback="未知创作者"
    root-class="creator-header"
    @retry="fetchDetail"
  >
    <template #stats>
      <span class="creator-header__stat">
        <span class="creator-header__stat-label">视频</span>
        <span class="creator-header__stat-value">{{ detail?.total_videos ?? 0 }}</span>
      </span>
      <span v-if="sourceLabel" class="creator-header__stat">
        <span class="creator-header__stat-label">来源</span>
        <span class="creator-header__stat-value creator-header__stat-value--text">{{ sourceLabel }}</span>
      </span>
      <a
        v-if="detail?.url"
        :href="detail.url"
        target="_blank"
        rel="noopener noreferrer"
        class="creator-header__site-link"
      >
        访问主页 <AppIcon name="externalLink" class="h-3.5 w-3.5" />
      </a>
    </template>

    <template #actions>
      <span v-if="loading && detail" class="creator-header__refreshing" role="status">正在更新创作者信息</span>
      <Button v-if="detail && detailError" type="button" variant="outline" size="sm" @click="fetchDetail">
        重试信息加载
      </Button>
    </template>

    <template #footer>
      <div v-if="detail && detailError" class="creator-header__refresh-error" role="alert">
        <AppIcon name="warning" class="h-4 w-4" />
        <span>{{ detailError }}</span>
      </div>
    </template>
  </ChannelIdentityHeader>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import ChannelIdentityHeader from '@/features/video/components/feed/ChannelIdentityHeader.vue'
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
.creator-header__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3rem;
}

.creator-header__stat-label {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
}

.creator-header__stat-value {
  color: hsl(var(--foreground));
  font-size: var(--app-text-sm);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.creator-header__stat-value--text {
  font-weight: 500;
}

.creator-header__site-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
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
  width: 100%;
  max-width: var(--app-content-media-max);
  margin: 0 auto;
  padding: 0.5rem var(--app-content-media-gutter);
  border-top: 1px solid hsl(var(--destructive) / 0.2);
  color: hsl(var(--destructive));
  font-size: var(--app-text-md);
}
</style>

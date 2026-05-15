<template>
  <div class="w-full">
    <div v-if="!isDesktop" class="flex min-h-[60vh] flex-col items-center justify-center p-10 text-center">
      <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
        <AppIcon name="search" class="h-10 w-10 text-muted-foreground/30" />
      </div>
      <h3 class="text-xl font-bold text-foreground/60">远端搜索仅桌面端可用</h3>
      <p class="mt-2 text-muted-foreground">桌面端会直接请求源站并使用本机站点会话。</p>
    </div>

    <div v-else-if="!trimmedQuery" class="flex min-h-[60vh] flex-col items-center justify-center p-10 text-center">
      <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
        <AppIcon name="search" class="h-10 w-10 text-muted-foreground/30" />
      </div>
      <h3 class="text-xl font-bold text-foreground/60">输入关键词开始远端搜索</h3>
      <p class="mt-2 text-muted-foreground">结果来自源站，不会写入本地数据。</p>
    </div>

    <div v-else>
      <div v-if="errorMessage" class="px-6 pt-6">
        <div class="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 p-4">
          <p class="text-sm font-medium text-destructive">{{ errorMessage }}</p>
          <button class="rounded-lg bg-destructive px-4 py-2 text-xs font-bold uppercase tracking-widest text-white" @click="load">
            重试
          </button>
        </div>
      </div>

      <div v-if="items.length > 0" class="grid grid-cols-1 gap-x-5 gap-y-10 p-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6">
        <button
          v-for="item in items"
          :key="item.site + ':' + item.url"
          type="button"
          class="group flex min-w-0 cursor-pointer flex-col gap-2.5 text-left"
          @click="openResult(item)"
        >
          <div class="relative aspect-video overflow-hidden rounded-lg bg-muted transition-colors group-hover:bg-muted/80">
            <img
              v-if="item.thumbnail"
              :src="item.thumbnail"
              :alt="item.title"
              loading="lazy"
              decoding="async"
              referrerpolicy="no-referrer"
              class="h-full w-full object-contain"
            >
            <div v-else class="absolute inset-0 flex items-center justify-center bg-muted">
              <AppIcon name="imageOff" class="h-6 w-6 text-muted-foreground/20" />
            </div>
            <span v-if="item.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
              {{ formatDuration(item.duration) }}
            </span>
          </div>

          <div class="flex min-w-0 flex-col gap-1 px-0.5">
            <h3 class="line-clamp-2 text-[14px] font-semibold leading-[1.3] tracking-tight text-foreground/90 transition-colors group-hover:text-primary">
              {{ item.title }}
            </h3>
            <div class="flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground/80">
              <span class="truncate">{{ item.uploader || siteLabel(item.site) }}</span>
              <span class="shrink-0 rounded-[4px] bg-accent/50 px-1 py-0 text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
                {{ siteLabel(item.site) }}
              </span>
            </div>
            <div class="text-[11px] font-medium text-muted-foreground/50">
              {{ displayDate(item) }}
            </div>
          </div>
        </button>
      </div>

      <div v-if="loading" class="grid grid-cols-1 gap-x-5 gap-y-10 p-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6">
        <VideoSkeleton v-for="i in 12" :key="i" :delay="i * 50" />
      </div>

      <div v-if="!loading && !errorMessage && items.length === 0" class="flex min-h-[60vh] flex-col items-center justify-center p-10 text-center">
        <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
          <AppIcon name="inbox" class="h-10 w-10 text-muted-foreground/30" />
        </div>
        <h3 class="text-xl font-bold text-foreground/60">未找到远端结果</h3>
        <p class="mt-2 text-muted-foreground">换个关键词或站点再试。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import { formatDuration } from '@/utils/dateFormat'

type RemoteSearchItem = {
  source: 'remote'
  site: string
  id?: string | number | null
  title: string
  url: string
  thumbnail?: string | null
  duration?: number | null
  publish_date?: string | null
  published_text?: string | null
  uploader?: string | null
  description?: string | null
}

const props = withDefaults(defineProps<{
  query?: string
  site?: string
  limit?: number
}>(), {
  query: '',
  site: '',
  limit: 30,
})

const emit = defineEmits(['loading-change', 'error'])

const isDesktop = window.desktopApp?.isDesktop === true
const items = ref<RemoteSearchItem[]>([])
const loading = ref(false)
const errorMessage = ref('')
const trimmedQuery = computed(() => String(props.query || '').trim())

let requestToken = 0

const siteLabel = (site: string) => {
  const labels: Record<string, string> = {
    bilibili: 'Bilibili',
    javdb: 'JavDB',
    pornhub: 'Pornhub',
    youtube: 'YouTube',
    youporn: 'YouPorn',
  }
  return labels[site] || site
}

const displayDate = (item: RemoteSearchItem) => {
  if (item.published_text) return item.published_text
  if (!item.publish_date) return ''
  const date = new Date(item.publish_date)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

const setLoading = (value: boolean) => {
  loading.value = value
  emit('loading-change', value)
}

const load = async () => {
  const query = trimmedQuery.value
  items.value = []
  errorMessage.value = ''

  if (!query || !isDesktop) {
    setLoading(false)
    return
  }

  const bridge = window.desktopApp
  if (typeof bridge?.searchRemoteVideos !== 'function') {
    errorMessage.value = '当前桌面端不支持远端搜索'
    emit('error', new Error(errorMessage.value))
    return
  }

  const currentToken = ++requestToken
  setLoading(true)
  try {
    const result = await bridge.searchRemoteVideos({
      query,
      site: props.site || 'all',
      limit: props.limit,
    })
    if (currentToken !== requestToken) return
    items.value = Array.isArray(result?.items) ? result.items : []
    if (Array.isArray(result?.errors) && result.errors.length > 0 && items.value.length === 0) {
      errorMessage.value = result.errors.join('；')
      emit('error', new Error(errorMessage.value))
    }
  } catch (error: any) {
    if (currentToken !== requestToken) return
    errorMessage.value = error?.message || '远端搜索失败'
    emit('error', error)
  } finally {
    if (currentToken === requestToken) setLoading(false)
  }
}

const openResult = async (item: RemoteSearchItem) => {
  if (!item.url) return
  await window.desktopApp?.openExternal?.(item.url)
}

watch(() => [props.query, props.site], load, { immediate: true })

defineExpose({ refresh: load })
</script>

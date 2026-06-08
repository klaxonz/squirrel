import { ref, shallowRef } from 'vue'
import { useDesktopBridge, getDesktopBridge } from '@/composables/useDesktopBridge'

type RemoteChannelProfile = {
  id?: string | number | null
  type?: string | null
  name?: string | null
  url?: string | null
  avatar?: string | null
  is_nsfw?: boolean | null
}

type RemoteVideoItem = {
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
  uploader_url?: string | null
  uploader_avatar?: string | null
  subscriptions?: RemoteChannelProfile[]
  actors?: RemoteChannelProfile[]
  description?: string | null
}

type RemoteChannelOptions = {
  site: string
  url: string
  profile?: RemoteChannelProfile
}

const REMOTE_CHANNEL_TIMEOUT_MS = 60000

const desktopBridge = useDesktopBridge()

const dedupeByUrl = <T extends { url: string }>(existing: T[], next: T[]): T[] => {
  const seen = new Set(existing.map((item) => item.url))
  return next.filter((item) => {
    if (!item.url || seen.has(item.url)) return false
    seen.add(item.url)
    return true
  })
}

export function useRemoteChannel() {
  const items = ref<RemoteVideoItem[]>([])
  const loading = ref(false)
  const allLoaded = ref(false)
  const error = ref('')
  const currentPage = ref(1)
  const nextCursor = shallowRef<unknown>(null)
  let requestToken = 0

  const resetState = () => {
    items.value = []
    currentPage.value = 1
    nextCursor.value = null
    allLoaded.value = false
    error.value = ''
  }

  const fetchPage = async (channel: RemoteChannelOptions, page: number, token: number): Promise<boolean> => {
    const rawBridge = getDesktopBridge()
    if (!rawBridge?.isDesktop || typeof rawBridge.getRemoteChannel !== 'function') {
      if (token === requestToken) error.value = '当前桌面端不支持远端频道'
      return false
    }

    loading.value = true
    let timer: ReturnType<typeof setTimeout> | undefined

    try {
      const remotePromise = rawBridge.getRemoteChannel({
        site: channel.site,
        url: channel.url,
        limit: 30,
        page,
        cursor: page > 1 && nextCursor.value ? { ...(nextCursor.value as Record<string, unknown>) } : undefined,
        profile: channel.profile
          ? {
              id: channel.profile.id ?? null,
              type: channel.profile.type ?? null,
              name: channel.profile.name ?? '',
              url: channel.profile.url ?? '',
              avatar: channel.profile.avatar ?? null,
              is_nsfw: channel.profile.is_nsfw === true,
            }
          : undefined,
      })
      if (!remotePromise) {
        if (token === requestToken) error.value = '远端频道加载失败'
        return false
      }

      const result = await Promise.race([
        remotePromise,
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => reject(new Error('远端频道加载超时')), REMOTE_CHANNEL_TIMEOUT_MS)
        }),
      ])
      if (token !== requestToken) return false

      const nextItems = (Array.isArray(result.items) ? result.items : []) as RemoteVideoItem[]
      if (page === 1) {
        items.value = nextItems
      } else {
        items.value = items.value.concat(dedupeByUrl(items.value, nextItems))
      }

      currentPage.value = page
      nextCursor.value = (result.next_cursor as unknown) || null
      allLoaded.value = result.has_more === false

      return true
    } catch (err: any) {
      if (token !== requestToken) return false
      error.value = err?.message || '远端频道加载失败'
      return false
    } finally {
      clearTimeout(timer)
      if (token === requestToken) loading.value = false
    }
  }

  const fetchRemote = async (channel: RemoteChannelOptions, isReset = false): Promise<void> => {
    if (!channel.site || !channel.url) return
    if (!isReset && (loading.value || allLoaded.value)) return

    if (isReset) resetState()

    const token = ++requestToken
    const page = isReset ? 1 : currentPage.value + 1
    await fetchPage(channel, page, token)
  }

  const loadMore = async (channel: RemoteChannelOptions): Promise<void> => {
    return fetchRemote(channel, false)
  }

  const refresh = async (channel: RemoteChannelOptions): Promise<void> => {
    return fetchRemote(channel, true)
  }

  return {
    items,
    loading,
    allLoaded,
    error,
    currentPage,
    nextCursor,
    fetchRemote,
    loadMore,
    refresh,
  }
}

export type { RemoteVideoItem, RemoteChannelOptions, RemoteChannelProfile }

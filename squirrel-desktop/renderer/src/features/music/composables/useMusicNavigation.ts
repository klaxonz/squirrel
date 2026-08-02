import { computed, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'

import { useNavigationHistory } from '@/shared/composables/useNavigationHistory'

export type MusicView =
  | 'home'
  | 'search'
  | 'fm'
  | 'ranks'
  | 'playlists'
  | 'playlist-detail'
  | 'user-playlist-detail'
  | 'artist-detail'
  | 'album-detail'
  | 'profile'
  | 'new-songs'
  | 'new-albums'
  | 'ai-recommend'
  | 'everyday-recommend'
  | 'favorites'

export type MusicDetailView = Extract<MusicView,
  'playlist-detail' | 'user-playlist-detail' | 'artist-detail' | 'album-detail'>

export type MusicDetailIdentity = {
  id: string
  kind?: 'playlist' | 'theme' | 'rank'
  rankCid?: string
}

const MUSIC_VIEWS = new Set<MusicView>([
  'home', 'search', 'fm', 'ranks', 'playlists', 'playlist-detail',
  'user-playlist-detail', 'artist-detail', 'album-detail', 'profile',
  'new-songs', 'new-albums', 'ai-recommend', 'everyday-recommend', 'favorites',
])

const DETAIL_VIEWS = new Set<MusicView>([
  'playlist-detail', 'user-playlist-detail', 'artist-detail', 'album-detail',
])

const DEFAULT_DETAIL_PARENTS: Record<MusicDetailView, MusicView> = {
  'playlist-detail': 'playlists',
  'user-playlist-detail': 'profile',
  'artist-detail': 'search',
  'album-detail': 'new-albums',
}

function queryValue(value: unknown): string {
  return Array.isArray(value) ? '' : String(value ?? '').trim()
}

export function parseMusicView(value: unknown): MusicView {
  const candidate = queryValue(value) as MusicView
  return MUSIC_VIEWS.has(candidate) ? candidate : 'home'
}

export function isMusicDetailView(view: MusicView): view is MusicDetailView {
  return DETAIL_VIEWS.has(view)
}

export function getMusicDetailIdentity(query: Record<string, unknown>): MusicDetailIdentity | null {
  const id = queryValue(query.id)
  if (!id) return null

  const kindValue = queryValue(query.kind)
  const kind = kindValue === 'playlist' || kindValue === 'theme' || kindValue === 'rank'
    ? kindValue
    : undefined
  const rankCid = queryValue(query.rank_cid) || undefined
  return { id, ...(kind ? { kind } : {}), ...(rankCid ? { rankCid } : {}) }
}

export function buildMusicViewQuery(
  view: MusicView,
  identity?: MusicDetailIdentity,
  from?: MusicView,
): LocationQueryRaw {
  if (view === 'home') return {}

  const query: LocationQueryRaw = { view }
  if (!isMusicDetailView(view) || !identity?.id.trim()) return query

  query.id = identity.id.trim()
  if (identity.kind) query.kind = identity.kind
  if (identity.rankCid) query.rank_cid = identity.rankCid
  if (from && !isMusicDetailView(from)) query.from = from
  return query
}

export function useMusicNavigation() {
  const route = useRoute()
  const router = useRouter()
  const nav = useNavigationHistory()

  const activeView = computed<MusicView>(() => parseMusicView(route.query.view))
  const isDetailView = computed(() => isMusicDetailView(activeView.value))

  watch(
    () => route.query.view,
    (rawView) => {
      const normalized = parseMusicView(rawView)
      const supplied = queryValue(rawView)
      if ((!supplied && rawView == null) || supplied === normalized) return
      void router.replace({ name: 'Music', query: buildMusicViewQuery(normalized) })
    },
    { immediate: true },
  )

  function detailParent(view: MusicDetailView = activeView.value as MusicDetailView): MusicView {
    const supplied = queryValue(route.query.from)
    if (supplied) {
      const requested = parseMusicView(supplied)
      if (!isMusicDetailView(requested)) return requested
    }
    return DEFAULT_DETAIL_PARENTS[view]
  }

  function navigateTo(view: MusicView, identity?: MusicDetailIdentity) {
    const current = activeView.value
    const from = isMusicDetailView(current)
      ? parseMusicView(route.query.from)
      : current
    const query = buildMusicViewQuery(view, identity, from)

    if (isMusicDetailView(view)) {
      if (route.fullPath !== router.resolve({ name: 'Music', query }).fullPath) {
        void router.push({ name: 'Music', query })
      }
      return
    }

    if (current !== view || route.fullPath !== router.resolve({ name: 'Music', query }).fullPath) {
      void router.replace({ name: 'Music', query })
    }
  }

  function goBack(): boolean {
    if (!isDetailView.value) return false
    if (nav.canGoBack.value) {
      void nav.goBack()
    } else {
      navigateTo(detailParent())
    }
    return true
  }

  function goHome() {
    navigateTo('home')
  }

  return {
    activeView,
    navigateTo,
    goBack,
    goHome,
    canGoBack: computed(() => isDetailView.value),
    isDetailView,
    detailParent: computed(() => isDetailView.value ? detailParent() : null),
  }
}

import { computed, ref } from 'vue'
import { getMusicRecommendations, reportFmGarbage, addMusicUserPlaylistTrack, type MusicTrack } from '@/shared/api/music'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { Logger } from '@/shared/lib/logger'
import { isApiError } from '@/shared/lib/apiError'

export type FmMode = 'normal' | 'small' | 'peak'

export function useMusicFm() {
  const store = useMusicPlayerStore()

  const mode = computed({
    get: () => store.fmMode,
    set: (v) => { store.fmMode = v },
  })
  const poolId = computed({
    get: () => store.fmPoolId,
    set: (v) => { store.fmPoolId = v },
  })
  const batch = ref<MusicTrack[]>([])
  const batchIndex = ref(0)
  const loading = ref(false)
  const hearted = ref<Record<string, boolean>>({})
  const liking = ref(false)
  const error = ref('')

  const queueLen = computed(() => Math.max(0, batch.value.length - batchIndex.value - 1))

  async function loadBatch(isNext = false, autoPlay = true, _userPlaylists: { id: string; name: string }[] = []) {
    loading.value = true
    error.value = ''

    const params: Record<string, unknown> = {
      mode: mode.value,
      song_pool_id: poolId.value,
    }

    if (isNext && store.currentTrack) {
      params.hash = store.currentTrack.hash
      params.playtime = Math.max(0, Math.floor(store.currentTime))
      params.remain_songcnt = queueLen.value
    }

    try {
      const data = await getMusicRecommendations(params)
      if (isNext) {
        const newItems = data?.items || []
        const seen = new Set(batch.value.map((t: MusicTrack) => t.hash || t.id))
        const fresh = newItems.filter(t => !seen.has(t.hash || t.id))
        const appendStart = batch.value.length
        batch.value = [...batch.value, ...fresh]

        if (fresh.length && autoPlay) {
          store.playQueue(batch.value, appendStart)
        } else {
          Logger.warn('FM batch exhausted, no more tracks returned')
        }
        return
      }

      batch.value = data?.items || []
      batchIndex.value = 0
      hearted.value = {}

      if (batch.value.length && autoPlay) {
        store.playQueue(batch.value, 0)
      }
    } catch (err) {
      error.value = isApiError(err) ? err.message : '加载失败'
      Logger.error('Failed to load FM batch', err)
    } finally {
      loading.value = false
    }
  }

  async function like(track: MusicTrack, userPlaylists: { id: string; name: string }[]) {
    if (!track.hash || hearted.value[track.hash] || liking.value) return

    const targetId = userPlaylists.find(pl => pl.name === '我喜欢')?.id
    if (!targetId) {
      error.value = '未找到「我喜欢」歌单，请先登录酷狗账号'
      return false
    }

    const hash = track.hash
    // Optimistic heart — rolled back if the like API fails.
    hearted.value = { ...hearted.value, [hash]: true }
    liking.value = true

    try {
      await addMusicUserPlaylistTrack({
        list_id: targetId,
        track: {
          title: track.title,
          hash: track.hash,
          album_id: track.album_id,
          album_audio_id: track.album_audio_id,
        },
      })
      return true
    } catch (err) {
      Logger.error('Failed to like FM track', err)
      hearted.value = { ...hearted.value, [hash]: false }
      error.value = '收藏失败，请重试'
      return false
    } finally {
      liking.value = false
    }
  }

  async function dislike() {
    if (!store.currentTrack) return

    loading.value = true
    error.value = ''

    try {
      const data = await reportFmGarbage({
        hash: store.currentTrack.hash,
        playtime: Math.max(0, Math.floor(store.currentTime)),
        mode: mode.value,
        song_pool_id: poolId.value,
      })

      const idx = batch.value.findIndex(t => t.hash === store.currentTrack?.hash)
      if (idx !== -1) {
        batch.value.splice(idx, 1)
        if (batchIndex.value > idx) {
          batchIndex.value--
        }
      }

      const newItems = data?.items || []
      if (newItems.length) {
        batch.value.push(...newItems)
      }

      if (batch.value.length > 0) {
        const nextIdx = Math.min(batchIndex.value, batch.value.length - 1)
        batchIndex.value = nextIdx
        const nextTrack = batch.value[nextIdx]
        if (nextTrack) {
          store.playQueue(batch.value, nextIdx)
        }
      } else {
        store.clear()
      }
    } catch (err) {
      error.value = isApiError(err) ? err.message : '操作失败'
      Logger.error('Failed to report FM garbage', err)
    } finally {
      loading.value = false
    }
  }

  function playFirst() {
    if (batch.value.length) {
      store.playQueue(batch.value, 0)
    }
  }

  function playAt(index: number) {
    if (index >= 0 && index < batch.value.length) {
      batchIndex.value = index
      store.playQueue(batch.value, index)
    }
  }

  async function next() {
    if (batchIndex.value < batch.value.length - 1) {
      batchIndex.value++
      const nextTrack = batch.value[batchIndex.value]
      if (nextTrack) {
        store.playTrack(nextTrack)
      }
    } else {
      await loadBatch(true)
    }
  }

  async function switchMode(newMode: FmMode) {
    if (mode.value === newMode) return
    mode.value = newMode
    await loadBatch()
  }

  async function switchPool(newPoolId: string) {
    if (poolId.value === newPoolId) return
    poolId.value = newPoolId
    await loadBatch()
  }

  const modeText = computed(() => {
    if (mode.value === 'normal') return '为你推荐 · 发现'
    if (mode.value === 'small') return '为你推荐 · 小众'
    return '为你推荐 · 30s'
  })

  return {
    mode,
    poolId,
    batch,
    batchIndex,
    loading,
    hearted,
    liking,
    error,
    queueLen,
    modeText,
    loadBatch,
    like,
    dislike,
    playFirst,
    playAt,
    next,
    switchMode,
    switchPool,
  }
}

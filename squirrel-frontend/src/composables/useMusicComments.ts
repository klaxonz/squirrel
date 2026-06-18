import { computed, ref } from 'vue'
import { getMusicSongComments, getMusicCommentCounts, type MusicComment } from '@/api/music'
import { Logger } from '@/utils/logger'

export function useMusicComments() {
  const comments = ref<MusicComment[]>([])
  const loading = ref(false)
  const error = ref('')
  const page = ref(1)
  const total = ref(0)
  const count = ref(0)

  let lastTrackId = ''

  const hasMore = computed(() => comments.value.length < total.value)

  async function load(albumAudioId: string, reset = true) {
    if (!albumAudioId) return

    if (reset) {
      comments.value = []
      page.value = 1
      total.value = 0
    }

    loading.value = true
    error.value = ''

    const { data, error: err } = await getMusicSongComments({
      mixsongid: albumAudioId,
      page: page.value,
      page_size: 20,
    })

    loading.value = false

    if (err) {
      error.value = err.message || '加载评论失败'
      Logger.error('Failed to load song comments', err)
      return
    }

    const items = data?.items || []
    comments.value = reset ? items : [...comments.value, ...items]
    total.value = data?.total || comments.value.length
  }

  async function loadMore(albumAudioId: string) {
    if (loading.value || !hasMore.value) return
    page.value++
    await load(albumAudioId, false)
  }

  async function loadCount(hash: string) {
    if (!hash) return
    const { data } = await getMusicCommentCounts(hash)
    if (data) {
      count.value = data.count
    }
  }

  function switchToComments(albumAudioId: string) {
    if (!albumAudioId || albumAudioId === lastTrackId) return
    lastTrackId = albumAudioId
    load(albumAudioId, true)
  }

  function resetForNewTrack() {
    comments.value = []
    lastTrackId = ''
    count.value = 0
  }

  return {
    comments,
    loading,
    error,
    page,
    total,
    count,
    hasMore,
    load,
    loadMore,
    loadCount,
    switchToComments,
    resetForNewTrack,
  }
}

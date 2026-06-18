import { defineStore } from 'pinia'
import { computed, nextTick, ref, shallowRef, watch } from 'vue'
import { getMusicLyric, getMusicPlayUrl, uploadMusicPlayHistory, type MusicLyricLine, type MusicTrack } from '@/api/music'
import { Logger } from '@/utils/logger'

export type RepeatMode = 'all' | 'one' | 'none'

const PLAYER_SESSION_KEY = 'squirrel:music:player-session'

type MusicPlayerSession = {
  currentTrack: MusicTrack | null
  queue: MusicTrack[]
  queueIndex: number
  currentTime: number
  volume: number
  shuffle: boolean
  repeat: RepeatMode
  fmMode: 'normal' | 'small' | 'peak'
  fmPoolId: string
}

export const useMusicPlayerStore = defineStore('musicPlayer', () => {
  const currentTrack = ref<MusicTrack | null>(null)
  const queue = ref<MusicTrack[]>([])
  const queueIndex = ref(-1)

  const playing = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const audioSrc = ref('')

  const quality = ref('128')
  const volume = ref(0.7)
  const shuffle = ref(false)
  const repeat = ref<RepeatMode>('all')
  const fmMode = ref<'normal' | 'small' | 'peak'>('normal')
  const fmPoolId = ref('0')
  const resolvingUrl = ref(false)
  const error = ref('')
  const lyricLines = ref<MusicLyricLine[]>([])
  const lyricLoading = ref(false)
  const lyricError = ref('')

  const audioRef = shallowRef<HTMLAudioElement | null>(null)
  let lyricRequestId = 0
  // Cache for prefetched play URLs to avoid re-fetching
  const urlCache = new Map<string, string>()
  let prefetchAbortId = 0

  const savedSession = ref<MusicPlayerSession | null>(loadSession())
  const lastSessionTrack = computed(() => currentTrack.value || savedSession.value?.currentTrack || null)

  const currentLyricIndex = computed(() => {
    if (lyricLines.value.length === 0) return -1
    for (let index = lyricLines.value.length - 1; index >= 0; index--) {
      if (currentTime.value >= lyricLines.value[index].time) {
        return index
      }
    }
    return -1
  })

  function setAudioRef(el: HTMLAudioElement | null) {
    audioRef.value = el
    if (!el) {
      playing.value = false
      return
    }
    el.volume = volume.value
    if (audioSrc.value) {
      el.src = audioSrc.value
      if (currentTime.value > 0) {
        seekAfterAudioReady(currentTime.value)
      }
    }
    syncPlayState()
  }

  function playTrack(track: MusicTrack) {
    const idx = queue.value.findIndex((t) => t.hash === track.hash)
    if (idx !== -1) {
      queueIndex.value = idx
    } else {
      queue.value.push(track)
      queueIndex.value = queue.value.length - 1
    }
    currentTrack.value = track
    loadLyric(track)
    _resolveAndPlay(track)
  }

  /** Insert a track to play immediately after the current one */
  function insertNext(track: MusicTrack) {
    // If already in queue, remove it first to avoid duplicates
    const existIdx = queue.value.findIndex((t) => t.hash === track.hash)
    if (existIdx !== -1) {
      queue.value.splice(existIdx, 1)
      if (queueIndex.value > existIdx) {
        queueIndex.value--
      }
    }
    const insertAt = queueIndex.value + 1
    queue.value.splice(insertAt, 0, track)
    if (queueIndex.value >= insertAt) {
      queueIndex.value++
    }
  }

  function playQueue(tracks: MusicTrack[], startIndex = 0) {
    queue.value = tracks
    queueIndex.value = startIndex
    currentTrack.value = tracks[startIndex] ?? null
    if (currentTrack.value) {
      loadLyric(currentTrack.value)
      _resolveAndPlay(currentTrack.value)
    }
  }

  function continueLastSession() {
    const session = savedSession.value
    if (!session?.currentTrack) return false

    const nextQueue = session.queue.length ? session.queue : [session.currentTrack]
    const nextIndex = Math.min(Math.max(session.queueIndex, 0), nextQueue.length - 1)
    const nextTrack = nextQueue[nextIndex] || session.currentTrack
    queue.value = nextQueue
    queueIndex.value = nextIndex
    currentTrack.value = nextTrack
    currentTime.value = session.currentTime || 0
    duration.value = nextTrack.duration || 0
    loadLyric(nextTrack)
    _resolveAndPlay(nextTrack, currentTime.value)
    return true
  }

  function togglePlayback() {
    if (!currentTrack.value) return
    if (!audioSrc.value) {
      _resolveAndPlay(currentTrack.value)
      return
    }
    if (!audioRef.value) return
    if (audioRef.value.paused) {
      audioRef.value.play().catch((err) => {
        markPlaybackError('播放失败，当前歌曲可能不可播放')
        Logger.error('Failed to play music audio', err)
      })
    } else {
      audioRef.value.pause()
    }
  }

  function playPrevious() {
    _step(-1)
  }

  function playNext() {
    _step(1)
  }

  function seekTo(time: number) {
    if (!audioRef.value) return
    audioRef.value.currentTime = time
    currentTime.value = time
  }

  function setVolume(val: number) {
    volume.value = val
    if (audioRef.value) {
      audioRef.value.volume = val
    }
  }

  function setQuality(val: string) {
    quality.value = val
    if (currentTrack.value) {
      _resolveAndPlay(currentTrack.value)
    }
  }

  function syncAudioState() {
    if (!audioRef.value) return
    currentTime.value = audioRef.value.currentTime || 0
    duration.value = audioRef.value.duration || currentTrack.value?.duration || 0
  }

  function syncPlayState() {
    if (!audioRef.value) {
      playing.value = false
      return
    }
    playing.value = !audioRef.value.paused
  }

  function clear() {
    currentTrack.value = null
    queue.value = []
    queueIndex.value = -1
    playing.value = false
    currentTime.value = 0
    duration.value = 0
    audioSrc.value = ''
    error.value = ''
    lyricLines.value = []
    lyricError.value = ''
    lyricLoading.value = false
    savedSession.value = null
    localStorage.removeItem(PLAYER_SESSION_KEY)
  }

  function clearQueue() {
    // Keep current track, clear the rest
    if (currentTrack.value) {
      queue.value = [currentTrack.value]
      queueIndex.value = 0
    } else {
      queue.value = []
      queueIndex.value = -1
    }
  }

  function removeFromQueue(hash: string) {
    const idx = queue.value.findIndex((t) => t.hash === hash)
    if (idx === -1) return
    queue.value.splice(idx, 1)
    if (queueIndex.value === idx) {
      queueIndex.value = -1
      currentTrack.value = null
      audioSrc.value = ''
      lyricLines.value = []
      savedSession.value = null
      localStorage.removeItem(PLAYER_SESSION_KEY)
    } else if (queueIndex.value > idx) {
      queueIndex.value--
    }
  }

  function reorderQueue(fromIndex: number, toIndex: number) {
    if (fromIndex === toIndex) return
    const [moved] = queue.value.splice(fromIndex, 1)
    queue.value.splice(toIndex, 0, moved)

    if (queueIndex.value === fromIndex) {
      queueIndex.value = toIndex
    } else if (fromIndex < queueIndex.value && toIndex >= queueIndex.value) {
      queueIndex.value--
    } else if (fromIndex > queueIndex.value && toIndex <= queueIndex.value) {
      queueIndex.value++
    }
  }

  function _step(offset: number) {
    if (queue.value.length === 0) return
    let nextIdx: number
    if (shuffle.value) {
      nextIdx = Math.floor(Math.random() * queue.value.length)
    } else {
      nextIdx = (queueIndex.value + offset + queue.value.length) % queue.value.length
    }
    const nextTrack = queue.value[nextIdx]
    if (nextTrack) {
      queueIndex.value = nextIdx
      currentTrack.value = nextTrack
      loadLyric(nextTrack)
      _resolveAndPlay(nextTrack)
    }
  }

  async function loadLyric(track: MusicTrack) {
    lyricRequestId++
    const requestId = lyricRequestId
    lyricLines.value = []
    lyricError.value = ''
    if (!track.hash || !track.title) return

    lyricLoading.value = true
    const { data, error: err } = await getMusicLyric({
      title: track.title,
      artist: track.artist,
      hash: track.hash,
      album_audio_id: track.album_audio_id || undefined,
      duration: track.duration,
    })
    if (requestId !== lyricRequestId) return

    lyricLoading.value = false
    if (err) {
      lyricError.value = err.message
      Logger.error('Failed to load music lyric', err)
      return
    }
    lyricLines.value = data?.lines || []
  }

  async function _resolveAndPlay(track: MusicTrack, startAt = 0) {
    if (!track.hash) return
    resolvingUrl.value = true
    error.value = ''
    playing.value = false
    audioSrc.value = ''
    currentTime.value = startAt
    duration.value = track.duration || 0

    // Check URL cache first
    const cacheKey = `${track.hash}:${quality.value}`
    const cached = urlCache.get(cacheKey)
    if (cached) {
      resolvingUrl.value = false
      audioSrc.value = cached
      if (startAt > 0) seekAfterAudioReady(startAt)
      void _uploadPlayHistory(track)
      void _prefetchNextTrack()
      await nextTick()
      return
    }

    const { data, error: err } = await getMusicPlayUrl({
      hash: track.hash,
      album_audio_id: track.album_audio_id || undefined,
      quality: quality.value,
    })
    resolvingUrl.value = false
    if (err || !data?.url) {
      markPlaybackError(err?.message || '当前歌曲没有可播放地址，可能是无版权、VIP 或地区限制')
      Logger.error('Failed to resolve music play url', err || data)
      return
    }
    urlCache.set(cacheKey, data.url)
    // Limit cache size to 50 entries
    if (urlCache.size > 50) {
      const firstKey = urlCache.keys().next().value
      if (firstKey) urlCache.delete(firstKey)
    }
    audioSrc.value = data.url
    if (startAt > 0) seekAfterAudioReady(startAt)
    void _uploadPlayHistory(track)
    void _prefetchNextTrack()
    await nextTick()
  }

  function markPlaybackError(message: string) {
    resolvingUrl.value = false
    playing.value = false
    audioSrc.value = ''
    error.value = message
  }

  function seekAfterAudioReady(time: number) {
    nextTick(() => {
      if (!audioRef.value || time <= 0) return
      const applySeek = () => {
        if (!audioRef.value) return
        audioRef.value.currentTime = Math.min(time, audioRef.value.duration || time)
      }
      if (audioRef.value.readyState >= 1) {
        applySeek()
      } else {
        audioRef.value.addEventListener('loadedmetadata', applySeek, { once: true })
      }
    })
  }

  /** Prefetch the next track's play URL in the background */
  async function _prefetchNextTrack() {
    if (queue.value.length <= 1) return
    prefetchAbortId++
    const myId = prefetchAbortId
    // ponytail: shuffle can't be predicted, so the sequential next is always
    // the only prefetch candidate regardless of shuffle state.
    const nextIdx = (queueIndex.value + 1) % queue.value.length
    const nextTrack = queue.value[nextIdx]
    if (!nextTrack?.hash) return
    const nextKey = `${nextTrack.hash}:${quality.value}`
    if (urlCache.has(nextKey)) return
    const { data } = await getMusicPlayUrl({
      hash: nextTrack.hash,
      album_audio_id: nextTrack.album_audio_id || undefined,
      quality: quality.value,
    })
    if (myId !== prefetchAbortId) return // Aborted by new prefetch
    if (data?.url) {
      urlCache.set(nextKey, data.url)
    }
  }

  async function _uploadPlayHistory(track: MusicTrack) {
    if (!track.album_audio_id) return
    const { error: err } = await uploadMusicPlayHistory({
      album_audio_id: track.album_audio_id,
      played_at: Math.floor(Date.now() / 1000),
      play_count: 1,
    })
    if (err) {
      Logger.error('Failed to upload music play history', err)
    }
  }

  function loadSession(): MusicPlayerSession | null {
    try {
      const raw = localStorage.getItem(PLAYER_SESSION_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw) as Partial<MusicPlayerSession>
      if (!parsed.currentTrack?.hash) return null
      return {
        currentTrack: parsed.currentTrack,
        queue: Array.isArray(parsed.queue) ? parsed.queue : [parsed.currentTrack],
        queueIndex: Number.isFinite(parsed.queueIndex) ? Number(parsed.queueIndex) : 0,
        currentTime: Number.isFinite(parsed.currentTime) ? Number(parsed.currentTime) : 0,
        volume: Number.isFinite(parsed.volume) ? Number(parsed.volume) : 0.7,
        shuffle: parsed.shuffle === true,
        repeat: parsed.repeat === 'none' || parsed.repeat === 'one' ? parsed.repeat : 'all',
        fmMode: parsed.fmMode === 'small' || parsed.fmMode === 'peak' ? parsed.fmMode : 'normal',
        fmPoolId: typeof parsed.fmPoolId === 'string' ? parsed.fmPoolId : '0',
      }
    } catch {
      return null
    }
  }

  function persistSession() {
    if (!currentTrack.value) return
    const session: MusicPlayerSession = {
      currentTrack: currentTrack.value,
      queue: queue.value,
      queueIndex: queueIndex.value,
      currentTime: currentTime.value,
      volume: volume.value,
      shuffle: shuffle.value,
      repeat: repeat.value,
      fmMode: fmMode.value,
      fmPoolId: fmPoolId.value,
    }
    savedSession.value = session
    localStorage.setItem(PLAYER_SESSION_KEY, JSON.stringify(session))
  }

  if (savedSession.value) {
    volume.value = savedSession.value.volume
    shuffle.value = savedSession.value.shuffle
    repeat.value = savedSession.value.repeat
    fmMode.value = savedSession.value.fmMode
    fmPoolId.value = savedSession.value.fmPoolId
  }

  watch(
    [currentTrack, queue, queueIndex, currentTime, volume, shuffle, repeat, fmMode, fmPoolId],
    persistSession,
    { deep: true },
  )

  function _onEnded() {
    if (repeat.value === 'one') {
      if (audioRef.value) {
        audioRef.value.currentTime = 0
        audioRef.value.play().catch((err) => Logger.error('Failed to replay music audio', err))
      }
      return
    }
    if (repeat.value === 'all' || shuffle.value) {
      playNext()
    } else {
      playing.value = false
    }
  }

  return {
    currentTrack,
    queue,
    queueIndex,
    playing,
    currentTime,
    duration,
    audioSrc,
    quality,
    volume,
    shuffle,
    repeat,
    fmMode,
    fmPoolId,
    resolvingUrl,
    error,
    lyricLines,
    lyricLoading,
    lyricError,
    currentLyricIndex,
    audioRef,
    savedSession,
    lastSessionTrack,
    setAudioRef,
    playTrack,
    playQueue,
    continueLastSession,
    togglePlayback,
    playPrevious,
    playNext,
    seekTo,
    setVolume,
    setQuality,
    syncAudioState,
    syncPlayState,
    clear,
    insertNext,
    clearQueue,
    removeFromQueue,
    reorderQueue,
    markPlaybackError,
    loadLyric,
    _onEnded,
  }
})

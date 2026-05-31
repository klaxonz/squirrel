import { defineStore } from 'pinia'
import { computed, nextTick, ref, shallowRef } from 'vue'
import { getMusicLyric, getMusicPlayUrl, uploadMusicPlayHistory, type MusicLyricLine, type MusicTrack } from '@/api/music'
import { Logger } from '@/utils/logger'

export type RepeatMode = 'all' | 'one' | 'none'

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
  const resolvingUrl = ref(false)
  const error = ref('')
  const lyricLines = ref<MusicLyricLine[]>([])
  const lyricLoading = ref(false)
  const lyricError = ref('')

  const audioRef = shallowRef<HTMLAudioElement | null>(null)
  let lyricRequestId = 0

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

  function playQueue(tracks: MusicTrack[], startIndex = 0) {
    queue.value = tracks
    queueIndex.value = startIndex
    currentTrack.value = tracks[startIndex] ?? null
    if (currentTrack.value) {
      loadLyric(currentTrack.value)
      _resolveAndPlay(currentTrack.value)
    }
  }

  function togglePlayback() {
    if (!currentTrack.value) return
    if (!audioSrc.value) {
      _resolveAndPlay(currentTrack.value)
      return
    }
    if (!audioRef.value) return
    if (audioRef.value.paused) {
      audioRef.value.play().catch((err) => Logger.error('Failed to play music audio', err))
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
    if (!audioRef.value) return
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
    } else if (queueIndex.value > idx) {
      queueIndex.value--
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

  async function _resolveAndPlay(track: MusicTrack) {
    if (!track.hash) return
    resolvingUrl.value = true
    error.value = ''
    currentTime.value = 0
    duration.value = track.duration || 0
    const { data, error: err } = await getMusicPlayUrl({
      hash: track.hash,
      album_audio_id: track.album_audio_id || undefined,
      quality: quality.value,
    })
    resolvingUrl.value = false
    if (err || !data?.url) {
      error.value = err?.message || '当前歌曲没有可播放地址'
      Logger.error('Failed to resolve music play url', err || data)
      return
    }
    audioSrc.value = data.url
    void _uploadPlayHistory(track)
    await nextTick()
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
    resolvingUrl,
    error,
    lyricLines,
    lyricLoading,
    lyricError,
    currentLyricIndex,
    audioRef,
    setAudioRef,
    playTrack,
    playQueue,
    togglePlayback,
    playPrevious,
    playNext,
    seekTo,
    setVolume,
    setQuality,
    syncAudioState,
    syncPlayState,
    clear,
    removeFromQueue,
    loadLyric,
    _onEnded,
  }
})

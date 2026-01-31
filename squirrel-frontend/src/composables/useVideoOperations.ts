import { getVideoUrlInfo } from '@/api'
import { Logger } from '@/utils/logger'

type VideoId = string | number

type VideoQuality = {
  value: string
  label: string
  height?: number
  bandwidth?: number
  id?: string | number
  index?: number
}

type VideoLike = {
  id?: VideoId
  video_id?: VideoId
  stream_video_url?: string
  stream_audio_url?: string
  mpd_url?: string
  qualities?: VideoQuality[]
  if_downloaded?: boolean
  isPlaying?: boolean
  [key: string]: any
}

type VideoUrlOptions = {
  forceRefresh?: boolean
}

type ApiResult<T> = { data?: T | null; error?: any }

type VideoUrlInfo = {
  mpd_url?: string
  video_url?: string
  audio_url?: string
  qualities?: Array<{
    value: string
    label: string
    height?: number
    bandwidth?: number
    id?: string | number
    index?: number
  }>
}

export default function useVideoOperations() {
  const extractErrorCode = (msg: unknown) => {
    if (!msg || typeof msg !== 'string') return null
    const match = msg.match(/\(([^)]+)\)\s*$/)
    return match ? match[1] : null
  }

  const getVideoUrl = async (video: VideoLike, options: VideoUrlOptions = {}) => {
    const { forceRefresh = false } = options
    Logger.debug('[getVideoUrl] Called with video', {
      id: video?.id,
      hasStreamUrl: !!video?.stream_video_url,
      hasMpdUrl: !!video?.mpd_url
    })
    
    if (!forceRefresh && video && (video.stream_video_url || video.mpd_url)) {
      Logger.debug('[getVideoUrl] URL already exists, skipping API call')
      return true
    }

    if (forceRefresh) {
      if (video) {
        video.stream_video_url = ''
        video.stream_audio_url = ''
        video.mpd_url = ''
        video.qualities = undefined
      }
    }

    if (!video || !video.id) {
      throw Object.assign(new Error('无效的视频对象'), {code: 'BAD_REQUEST'})
    }

    try {
      if (video.if_downloaded) {
        video.stream_video_url = `/api/video/play/${video.video_id}`
        return true
      }

      // 统一通过后端获取播放链接（VideoUrlDto），后端会在 bilibili/YouTube 情况下返回 mpd_url 与可选清晰度
      Logger.debug('[getVideoUrl] Making API call to /api/video/url for video', video.id)
      const { data, error } = (await getVideoUrlInfo(video.id, { forceRefresh })) as ApiResult<VideoUrlInfo>

      if (error) {
        const msg = error.data?.msg || error.message
        const errCode = extractErrorCode(msg) || error.data?.code || error.type || 'UNKNOWN'
        throw Object.assign(new Error(msg || '无法获取播放链接'), { code: errCode })
      }

      const mpdUrl = data?.mpd_url
      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      const qualities = Array.isArray(data?.qualities) ? data.qualities : []

      if (qualities.length) {
        video.qualities = qualities.map((q) => ({ 
          value: q.value, 
          label: q.label, 
          height: q.height, 
          bandwidth: q.bandwidth, 
          id: q.id as any,
          index: q.index as any
        }))
      } else {
        video.qualities = undefined
      }

      if (mpdUrl) {
        video.mpd_url = mpdUrl
        return true
      }

      if (!videoUrl && !audioUrl) {
        throw Object.assign(new Error('无法获取播放链接'), {code: 'NO_STREAM_URL'})
      }

      video.stream_video_url = videoUrl || ''
      video.stream_audio_url = audioUrl || ''
      video.mpd_url = ''
      return true
    } catch (err) {
      throw err
    }
  }

  const playVideo = async (video: VideoLike, options: VideoUrlOptions = {}) => {
    await getVideoUrl(video, options)
    video.isPlaying = true
  }

  const changeVideo = async (newVideo: VideoLike, options: VideoUrlOptions = {}) => {
    await getVideoUrl(newVideo, options)
    return newVideo
  }

  const onVideoPlay = (video: VideoLike) => {
    video.isPlaying = true
  }

  const onVideoPause = (video: VideoLike) => {
    video.isPlaying = false
  }

  const onVideoEnded = (video: VideoLike) => {
    video.isPlaying = false
  }

  return {
    playVideo,
    changeVideo,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
  }
}

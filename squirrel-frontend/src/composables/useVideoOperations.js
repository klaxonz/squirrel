import axios from '../utils/axios';

export default function useVideoOperations() {
  const extractErrorCode = (msg) => {
    if (!msg || typeof msg !== 'string') return null
    const match = msg.match(/\(([^)]+)\)\s*$/)
    return match ? match[1] : null
  }

  const getVideoUrl = async (video, options = {}) => {
    const { forceRefresh = false } = options
    console.log('[getVideoUrl] Called with video:', {
      id: video?.id,
      hasStreamUrl: !!video?.stream_video_url,
      hasMpdUrl: !!video?.mpd_url
    })
    
    if (!forceRefresh && (video.stream_video_url || video.mpd_url)) {
      console.log('[getVideoUrl] URL already exists, skipping API call')
      return true
    }

    if (forceRefresh) {
      video.stream_video_url = ''
      video.stream_audio_url = ''
      video.mpd_url = ''
      video.qualities = undefined
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
      console.log('[getVideoUrl] Making API call to /api/video/url for video:', video.id)
      const response = await axios.get('/api/video/url', {
        params: {
          video_id: video.id,
          ...(forceRefresh ? { force_refresh: true } : {})
        }
      })

      const { code, msg, data } = response?.data || {}
      console.log('[Debug] 1. useVideoOperations: Received data from /api/video/url', data);

      if (code !== 0) {
        const errCode = extractErrorCode(msg) || code || 'UNKNOWN'
        throw Object.assign(new Error(msg || '无法获取播放链接'), {code: errCode})
      }

      const mpdUrl = data?.mpd_url
      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      const qualities = Array.isArray(data?.qualities) ? data.qualities : []

      if (qualities.length) {
        video.qualities = qualities.map(q => ({ 
          value: q.value, 
          label: q.label, 
          height: q.height, 
          bandwidth: q.bandwidth, 
          id: q.id,
          index: q.index
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

  const playVideo = async (video, options = {}) => {
    await getVideoUrl(video, options)
    video.isPlaying = true
  }

  const changeVideo = async (newVideo, options = {}) => {
    await getVideoUrl(newVideo, options)
    return newVideo
  }

  const onVideoPlay = (video) => {
    video.isPlaying = true
  }

  const onVideoPause = (video) => {
    video.isPlaying = false
  }

  const onVideoEnded = (video) => {
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

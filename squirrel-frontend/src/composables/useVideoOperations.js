import axios from '../utils/axios';

export default function useVideoOperations() {
  const extractErrorCode = (msg) => {
    if (!msg || typeof msg !== 'string') return null
    const match = msg.match(/\(([^)]+)\)\s*$/)
    return match ? match[1] : null
  }

  const getVideoUrl = async (video) => {
    if (video.stream_video_url || video.mpd_url) return true

    if (!video || !video.id) {
      const err = Object.assign(new Error('无效的视频对象'), { code: 'BAD_REQUEST' })
      throw err
    }

    try {
      if (video.if_downloaded) {
        video.stream_video_url = `/api/video/play/${video.video_id}`
        return true
      }

      // 统一通过后端获取播放链接（VideoUrlDto），后端会在 bilibili/YouTube 情况下返回 mpd_url 与可选清晰度
      const response = await axios.get('/api/video/url', {
        params: { video_id: video.id }
      })

      const { code, msg, data } = response?.data || {}
      console.log('[Debug] 1. useVideoOperations: Received data from /api/video/url', data);

      if (code !== 0) {
        const errCode = extractErrorCode(msg) || code || 'UNKNOWN'
        const err = Object.assign(new Error(msg || '无法获取播放链接'), { code: errCode })
        throw err
      }

      const mpdUrl = data?.mpd_url
      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      const qualities = Array.isArray(data?.qualities) ? data.qualities : []

      // 将清晰度选项透传给前端播放器用于显示
      if (qualities.length) {
        video.qualities = qualities.map(q => ({ value: q.value, label: q.label, height: q.height, bandwidth: q.bandwidth, id: q.id }))
      } else {
        video.qualities = undefined
      }

      if (mpdUrl) {
        console.log('[Debug] 1.1. useVideoOperations: DASH mode detected. Setting video.mpd_url =', mpdUrl);
        video.mpd_url = mpdUrl
        return true
      }

      if (!videoUrl && !audioUrl) {
        const err = Object.assign(new Error('无法获取播放链接'), { code: 'NO_STREAM_URL' })
        throw err
      }

      console.log('[Debug] 1.2. useVideoOperations: Non-DASH mode. Setting stream URLs.');
      video.stream_video_url = videoUrl || ''
      video.stream_audio_url = audioUrl || ''
      video.mpd_url = ''
      return true
    } catch (err) {
      throw err
    }
  }

  const playVideo = async (video) => {
    await getVideoUrl(video)
    video.isPlaying = true
  }

  const changeVideo = async (newVideo) => {
    await getVideoUrl(newVideo)
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

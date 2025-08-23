import axios from '../utils/axios';

export default function useVideoOperations() {
  const extractErrorCode = (msg) => {
    if (!msg || typeof msg !== 'string') return null
    const match = msg.match(/\(([^)]+)\)\s*$/)
    return match ? match[1] : null
  }

  const getVideoUrl = async (video) => {
    if (video.stream_video_url) return true

    if (!video || !video.id) {
      const err = Object.assign(new Error('无效的视频对象'), { code: 'BAD_REQUEST' })
      throw err
    }

    try {
      if (video.if_downloaded) {
        video.stream_video_url = `/api/video/play/${video.video_id}`
        return true
      }

      if (video.url.indexOf('bilibili.com') !== -1) {
        const response = await axios.get('/api/video/mpd', {
          params: { video_id: video.id }
        })
      } else {
        const response = await axios.get('/api/video/url', {
          params: { video_id: video.id }
        })
      }
      

      const { code, msg, data } = response?.data || {}
      if (code !== 0) {
        const errCode = extractErrorCode(msg) || code || 'UNKNOWN'
        const err = Object.assign(new Error(msg || '无法获取播放链接'), { code: errCode })
        throw err
      }

      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      if (!videoUrl && !audioUrl) {
        const err = Object.assign(new Error('无法获取播放链接'), { code: 'NO_STREAM_URL' })
        throw err
      }

      video.stream_video_url = videoUrl || ''
      video.stream_audio_url = audioUrl || ''
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

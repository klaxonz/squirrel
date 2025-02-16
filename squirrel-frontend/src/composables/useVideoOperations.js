import axios from '../utils/axios';

export default function useVideoOperations() {
  const getVideoUrl = async (video) => {
    if (!video.stream_video_url) {
      try {
        if (video.if_downloaded) {
          video.stream_video_url = `/api/video/play/${video.video_id}`;
        } else {
          const response = await axios.get('/api/video/url', {
            params: {
              video_id: video.id
            }
          });
          if (response.data.code === 0) {
            video.stream_video_url = response.data.data.video_url;
            video.stream_audio_url = response.data.data.audio_url;
          }
        }
      } catch (err) {
        console.error('获取视频地址失败:', err);
        return false;
      }
    }
    return true;
  };

  const playVideo = async (video) => {
    if (!(await getVideoUrl(video))) {
      return;
    }
    video.isPlaying = true;
  };

  const changeVideo = async (newVideo) => {
    if (!(await getVideoUrl(newVideo))) {
      return;
    }
    return newVideo;
  };

  const onVideoPlay = (video) => {
    video.isPlaying = true;
  };

  const onVideoPause = (video) => {
    video.isPlaying = false;
  };

  const onVideoEnded = (video) => {
    video.isPlaying = false;
  };

  return {
    playVideo,
    changeVideo,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
  };
}

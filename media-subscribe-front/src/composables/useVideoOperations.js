import { nextTick } from 'vue';
import axios from '../utils/axios';

export default function useVideoOperations(videos, videoRefs) {
  const playVideo = async (video) => {
    if (!video.video_url) {
      try {
        if (video.if_downloaded) {
          video.video_url = `/api/channel/video/play/${video.channel_id}/${video.video_id}`;
        } else {
          const response = await axios.get('/api/channel-video/video/url', {
            params: {
              channel_id: video.channel_id,
              video_id: video.video_id
            }
          });
          if (response.data.code === 0) {
            video.video_url = response.data.data;
          } else {
            throw new Error(response.data.msg || '获取视频地址失败');
          }
        }
      } catch (err) {
        console.error('获取视频地址失败:', err);
        return;
      }
    }

    video.isPlaying = true;

    // 停止其他正在播放的视频
    videos.value[video.tab].forEach(v => {
      if (v !== video && v.isPlaying) {
        v.isPlaying = false;
        const videoElement = videoRefs.value[v.id];
        if (videoElement) {
          videoElement.pause();
        }
      }
    });

    await nextTick();
    const videoElement = videoRefs.value[video.id];
    if (videoElement) {
      try {
        await videoElement.play();
      } catch (error) {
        console.error('自动播放失败:', error);
      }
    }
  };

  const onVideoPlay = (video) => {
    video.isPlaying = true;
  };

  const onVideoPause = (video) => {
    // 不改变 isPlaying 状态，允许用户暂停后继续播放
  };

  const onVideoEnded = (video) => {
    video.isPlaying = false;
  };

  const onFullscreenChange = (event) => {
    const videoElement = event.target;
    if (document.fullscreenElement) {
      const aspectRatio = videoElement.videoWidth / videoElement.videoHeight;
      videoElement.style.width = '100%';
      videoElement.style.height = '100%';
      videoElement.style.objectFit = aspectRatio < 1 ? 'contain' : 'cover';
    } else {
      onVideoMetadataLoaded({ target: videoElement });
    }
  };

  const onVideoMetadataLoaded = (event) => {
    const videoElement = event.target;
    const aspectRatio = videoElement.videoWidth / videoElement.videoHeight;
    
    if (aspectRatio < 1) {
      videoElement.style.width = '100%';
      videoElement.style.height = 'auto';
      videoElement.style.maxHeight = '100%';
    } else {
      videoElement.style.width = '100%';
      videoElement.style.height = '100%';
      videoElement.style.objectFit = 'contain';
    }
  };

  const setVideoRef = (id, el) => {
    if (el) videoRefs.value[id] = el;
  };

  const handleOrientationChange = () => {
    videos.value.forEach(video => {
      if (video.isPlaying) {
        const videoElement = videoRefs.value[video.id];
        if (videoElement && document.fullscreenElement) {
          videoElement.style.objectFit = window.screen.orientation.type.includes('portrait') ? 'contain' : 'cover';
        }
      }
    });
  };

  return {
    playVideo,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    onFullscreenChange,
    onVideoMetadataLoaded,
    setVideoRef,
    handleOrientationChange,
  };
}
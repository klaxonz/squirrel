import { ref, inject } from 'vue';
import axios from '../utils/axios';
import useToast from './useToast';

export default function useVideoOperations(videos, videoRefs) {
  const displayToast = inject('toast');
  const playbackError = ref(null);

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
            displayToast(response.data.msg || '获取视频地址失败');
          }
        }
      } catch (err) {
        console.error('获取视频地址失败:', err);
        playbackError.value = '获取视频地址失败';
        return;
      }
    }

    // 停止其他正在播放的视频
    Object.values(videos.value).forEach(tabVideos => {
      if (Array.isArray(tabVideos)) {
        tabVideos.forEach(v => {
          if (v !== video && v.isPlaying) {
            v.isPlaying = false;
              console.log('Video paused:', video.id)

            const playerInstance = videoRefs.value[v.id];
            if (playerInstance) {
              playerInstance.pause();
              console.log('Video paused:', video.id)
            }
          }
        });
      }
    });

    video.isPlaying = true;
    const playerInstance = videoRefs.value[video.id];
    if (playerInstance) {
      playerInstance.play();
    }
  };

  const retryPlay = (video) => {
    playbackError.value = null;
    playVideo(video);
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

  const setVideoRef = (id, playerInstance) => {
    if (playerInstance) videoRefs.value[id] = playerInstance;
  };

  const handleOrientationChange = () => {
    Object.values(videos.value).forEach(tabVideos => {
      tabVideos.forEach(video => {
        if (video.isPlaying) {
          const videoElement = videoRefs.value[video.id];
          if (videoElement && document.fullscreenElement) {
            videoElement.style.objectFit = window.screen.orientation.type.includes('portrait') ? 'contain' : 'cover';
          }
        }
      });
    });
  };

  const pauseVideo = (video) => {
    if (video.isPlaying) {
      const videoElement = videoRefs.value[video.id];
      console.log('Pause video:', videoElement)
      if (videoElement) {
        videoElement.pause();
        video.isPlaying = false;
      }
    }
  };

  const onVideoLeaveViewport = (video) => {
    pauseVideo(video);
  };

  const attemptAutoplay = async (videoId) => {
    const videoElement = videoRefs.value[videoId];
    if (videoElement) {
      try {
        await videoElement.play();
        // 如果成功播放，尝试取消静音
        videoElement.muted = false;
      } catch (error) {
        console.warn('Autoplay failed:', error);
        // 如果自动播放失败，保持静音状态并再次尝试播放
        videoElement.muted = true;
        try {
          await videoElement.play();
        } catch (innerError) {
          console.error('Autoplay failed even with muted video:', innerError);
        }
      }
    }
  };

  return {
    playVideo,
    retryPlay,
    playbackError,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    setVideoRef,
    handleOrientationChange,
    pauseVideo,
    attemptAutoplay,
    onVideoLeaveViewport,
  };
}
import { ref, inject, onMounted, onUnmounted } from 'vue';
import axios from '../utils/axios';

export default function useVideoOperations(videos, videoRefs) {
  const displayToast = inject('toast');
  const isFullscreen = ref(false);

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
        return;
      }
    }

    // 停止其他正在播放的视频
    Object.values(videos.value).forEach(tabVideos => {
      if (Array.isArray(tabVideos)) {
        tabVideos.forEach(v => {
          if (v !== video && v.isPlaying) {
            v.isPlaying = false;
          }
        });
      }
    });

    video.isPlaying = true;
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
    isFullscreen.value = !!document.fullscreenElement;
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
      const playerInstance = videoRefs.value[video.id];
      if (playerInstance && playerInstance.pause) {
        playerInstance.pause();
        video.isPlaying = false;
      }
    }
  };

  const onVideoLeaveViewport = (video) => {
    if (!isFullscreen.value) {
      pauseVideo(video);
    }
  };

  onMounted(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
  });

  onUnmounted(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
  });

  return {
    playVideo,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    onFullscreenChange,
    setVideoRef,
    handleOrientationChange,
    pauseVideo,
    onVideoLeaveViewport,
    isFullscreen
  };
}
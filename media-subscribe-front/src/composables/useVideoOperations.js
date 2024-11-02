import { ref, inject, onMounted, onUnmounted } from 'vue';
import axios from '../utils/axios';
import useCustomToast from "./useToast.js";

export default function useVideoOperations(videos, videoRefs) {
  const { displayToast } = useCustomToast();
  const isFullscreen = ref(false);

  const getVideoUrl = async (video) => {
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
            video.video_url = response.data.data.video_url;
            video.audio_url = response.data.data.audio_url;
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

  const changeVideo = async (newVideo) => {
    if (!(await getVideoUrl(newVideo))) {
      return;
    }

    // 停止当前正在播放的视频
    Object.values(videos.value).forEach(tabVideos => {
      if (Array.isArray(tabVideos)) {
        tabVideos.forEach(v => {
          if (v.isPlaying) {
            v.isPlaying = false;
          }
        });
      }
    });

    newVideo.isPlaying = true;

    // 返回更新后的视频对象
    return newVideo;
  };

  const onVideoPlay = (video) => {
    video.isPlaying = true;
    video.progressSavingInterval = startProgressSaving(video);
  };

  const onVideoPause = (video) => {
    clearInterval(video.progressSavingInterval);
    const playerInstance = videoRefs.value[video.id];
    if (playerInstance && playerInstance.currentTime) {
      saveVideoProgress(video, playerInstance.currentTime);
    }
  };

  const onVideoEnded = (video) => {
    video.isPlaying = false;
    clearInterval(video.progressSavingInterval);
    saveVideoProgress(video, 0); // 视频结束时，重置进度
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

  const saveVideoProgress = async (video, progress) => {
    try {
      await axios.post('/api/channel-video/save-progress', {
        channel_id: video.channel_id,
        video_id: video.video_id,
        progress: progress
      });
    } catch (error) {
      console.error('保存视频进度失败:', error);
    }
  };

  const getVideoProgress = async (video) => {
    try {
      const response = await axios.get('/api/channel-video/get-progress', {
        params: {
          channel_id: video.channel_id,
          video_id: video.video_id
        }
      });
      return response.data.data.progress;
    } catch (error) {
      console.error('获取视频进度失败:', error);
      return 0;
    }
  };

  const startProgressSaving = (video) => {
    return setInterval(() => {
      // const playerInstance = videoRefs.value[video.id];
      // if (playerInstance && playerInstance.currentTime) {
      //   saveVideoProgress(video, playerInstance.currentTime);
      // }
    }, 5000); // 每5秒保存一次进度
  };

  onMounted(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
  });

  onUnmounted(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
  });

  return {
    playVideo,
    changeVideo,
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    onFullscreenChange,
    setVideoRef,
    handleOrientationChange,
    pauseVideo,
    onVideoLeaveViewport,
    isFullscreen,
    saveVideoProgress,
    getVideoProgress,
    startProgressSaving
  };
}

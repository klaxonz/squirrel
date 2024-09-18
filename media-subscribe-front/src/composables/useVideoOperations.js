import { ref } from 'vue';
import axios from '../utils/axios';
import useToast from './useToast';

export default function useVideoOperations(videos, videoRefs) {
  const { displayToast } = useToast();
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
    if (Array.isArray(videos.value)) {
      videos.value.forEach(v => {
        if (v !== video && v.isPlaying) {
          v.isPlaying = false;
        }
      });
    } else if (typeof videos.value === 'object') {
      Object.values(videos.value).forEach(tabVideos => {
        if (Array.isArray(tabVideos)) {
          tabVideos.forEach(v => {
            if (v !== video && v.isPlaying) {
              v.isPlaying = false;
            }
          });
        }
      });
    }

    video.isPlaying = true;

    // 移除这里的播放逻辑，因为现在 VideoPlayer 组件会自动开始播放
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

  const setVideoRef = (id, el) => {
    if (el) videoRefs.value[id] = el;
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
      if (videoElement) {
        videoElement.pause();
        video.isPlaying = false;
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
    onFullscreenChange,
    onVideoMetadataLoaded,
    setVideoRef,
    handleOrientationChange,
    pauseVideo,
  };
}
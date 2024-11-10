import { ref, inject, onMounted, onUnmounted } from 'vue';
import axios from '../utils/axios';
import useCustomToast from "./useToast.js";

export default function useVideoOperations() {
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
    // Object.values(videos.value).forEach(tabVideos => {
    //   if (Array.isArray(tabVideos)) {
    //     tabVideos.forEach(v => {
    //       if (v !== video && v.isPlaying) {
    //         v.isPlaying = false;
    //       }
    //     });
    //   }
    // });

    video.isPlaying = true;
  };

  const changeVideo = async (newVideo) => {
    if (!(await getVideoUrl(newVideo))) {
      return;
    }

    // 停止当前正在播放的视频
    // Object.values(videos.value).forEach(tabVideos => {
    //   if (Array.isArray(tabVideos)) {
    //     tabVideos.forEach(v => {
    //       if (v.isPlaying) {
    //         v.isPlaying = false;
    //       }
    //     });
    //   }
    // });
    newVideo.isPlaying = true;
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

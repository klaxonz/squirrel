import axios from '../utils/axios';
import useCustomToast from './useToast';

export default function useOptionsMenu(videoRef) {
  const { displayToast } = useCustomToast();

  const toggleReadStatus = async (isRead) => {
    try {
      await axios.post('/api/channel-video/mark-read', {
        channel_id: videoRef.value.channel_id,
        video_id: videoRef.value.video_id,
        is_read: isRead
      });
      displayToast(`视频已标记为${isRead ? '已读' : '未读'}`);
    } catch (error) {
      console.error('更新阅读状态失败:', error);
      displayToast('更新阅读状态失败', { type: 'error' });
    }
  };

  const markReadBatch = async (isRead, direction) => {
    try {
      const channelId = videoRef.value.channel_id;
      const response = await axios.post('/api/channel-video/mark-read-batch', {
        is_read: isRead,
        channel_id: channelId,
        direction: direction,
        uploaded_at: videoRef.value.uploaded_at
      });

      if (response.data.code === 0) {
        displayToast(`已将${direction === 'above' ? '以上' : '以下'}视频标记为${isRead ? '已读' : '未读'}`);
      } else {
        throw new Error(response.data.msg || '批量更新阅读状态失败');
      }
    } catch (error) {
      console.error('批量更新阅读状态失败:', error);
      displayToast('批量更新阅读状态失败', { type: 'error' });
    }
  };

  const downloadVideo = async () => {
    try {
      const response = await axios.post('/api/channel-video/download', {
        channel_id: videoRef.value.channel_id,
        video_id: videoRef.value.video_id
      });

      if (response.data.code === 0) {
        displayToast('视频下载已开始，请查看下载列表');
        videoRef.value.if_downloaded = true;
      } else {
        displayToast('视频下载已开始，请查看下载列表');
      }
    } catch (error) {
      console.error('下载视频失败:', error);
      displayToast('下载视频失败: ' + (error.message || '未知错误'), { type: 'error' });
    }
  };

  const copyVideoLink = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(videoRef.value.url)
        .then(() => {
          displayToast('视频链接已复制到剪贴板');
        })
        .catch(err => {
          fallbackCopyTextToClipboard(videoRef.value.url);
        });
    } else {
      fallbackCopyTextToClipboard(videoRef.value.url);
    }
  };

  const fallbackCopyTextToClipboard = (text) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      const successful = document.execCommand('copy');
      const msg = successful ? '视频链接已复制到剪贴板' : '复制失败，请手动复制';
      displayToast(msg);
    } catch (err) {
      console.error('Fallback: Oops, unable to copy', err);
      displayToast('复制失败，请手动复制', { type: 'error' });
    }

    document.body.removeChild(textArea);
  };

  const toggleLikeVideo = async (targetStatus) => {
    try {
      const nextLikeStatus = videoRef.value.is_liked === targetStatus ? null : targetStatus;

      const response = await axios.post('/api/channel-video/toggle-like', {
        channel_id: videoRef.value.channel_id,
        video_id: videoRef.value.video_id,
        is_liked: nextLikeStatus
      });

      if (response.data.code === 0) {
        videoRef.value.is_liked = nextLikeStatus;
        
        const playlist = document.querySelector('.playlist-section');
        if (playlist) {
          const videos = playlist.querySelectorAll('.video-item');
          videos.forEach(video => {
            if (video.dataset.videoId === videoRef.value.video_id) {
              video.__vue__.$data.video.is_liked = nextLikeStatus;
            }
          });
        }
      } else {
        throw new Error(response.data.msg || '操作失败');
      }
    } catch (error) {
      console.error('切换喜欢状态失败:', error);
    }
  };

  return {
    toggleReadStatus,
    markReadBatch,
    downloadVideo,
    copyVideoLink,
    toggleLikeVideo,
  };
}

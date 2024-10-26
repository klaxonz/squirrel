import { inject } from 'vue';
import axios from '../utils/axios';

export default function useOptionsMenu(video, refreshContent) {
  const displayToast = inject('toast');

  const toggleReadStatus = async (isRead) => {
    try {
      await axios.post('/api/channel-video/mark-read', {
        channel_id: video.channel_id,
        video_id: video.video_id,
        is_read: isRead
      });
      displayToast(`视频已标记为${isRead ? '已读' : '未读'}`);
      await refreshContent();
    } catch (error) {
      console.error('更新阅读状态失败:', error);
      displayToast('更新阅读状态失败', true);
    }
  };

  const markReadBatch = async (isChannel, isRead, direction) => {
    try {
      const channelId = isChannel ? video.channel_id : null;
      const response = await axios.post('/api/channel-video/mark-read-batch', {
        is_read: isRead,
        channel_id: channelId,
        direction: direction,
        uploaded_at: video.uploaded_at
      });

      if (response.data.code === 0) {
        displayToast(`已将${direction === 'above' ? '以上' : '以下'}视频标记为${isRead ? '已读' : '未读'}`);
        await refreshContent();
      } else {
        throw new Error(response.data.msg || '批量更新阅读状态失败');
      }
    } catch (error) {
      console.error('批量更新阅读状态失败:', error);
      displayToast('批量更新阅读状态失败', true);
    }
  };

  const downloadVideo = async () => {
    try {
      const response = await axios.post('/api/channel-video/download', {
        channel_id: video.channel_id,
        video_id: video.video_id
      });

      if (response.data.code === 0) {
        displayToast('视频下载已开始，请查看下载列表');
        video.if_downloaded = true;
      } else {
        displayToast('视频下载已开始，请查看下载列表');
      }
    } catch (error) {
      console.error('下载视频失败:', error);
      displayToast('下载视频失败: ' + (error.message || '未知错误'), true);
    }
  };

  const copyVideoLink = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(video.url)
        .then(() => {
          displayToast('视频链接已复制到剪贴板');
        })
        .catch(err => {
          fallbackCopyTextToClipboard(video.url);
        });
    } else {
      fallbackCopyTextToClipboard(video.url);
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
      displayToast('复制失败，请手动复制');
    }

    document.body.removeChild(textArea);
  };

  const dislikeVideo = () => {
    // 实现不喜欢视频的逻辑
    displayToast('已标记为不喜欢');
  };

  return {
    toggleReadStatus,
    markReadBatch,
    downloadVideo,
    copyVideoLink,
    dislikeVideo,
  };
}

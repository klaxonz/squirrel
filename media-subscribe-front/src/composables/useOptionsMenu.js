import axios from '../utils/axios';
import useCustomToast from './useToast';

export default function useOptionsMenu(videoRef) {
  const { displayToast } = useCustomToast();

  const downloadVideo = async () => {
    try {
      const response = await axios.post('/api/video/download', {
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

  return {
    downloadVideo,
    copyVideoLink,
  };
}

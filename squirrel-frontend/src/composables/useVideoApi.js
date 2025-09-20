import axios from '../utils/axios';

export function useVideoApi() {
  const getVideoDetail = async (videoId) => {
    try {
      const response = await axios.get('/api/video/detail', { params: { video_id: videoId } });
      if (response.data.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data.msg || '获取视频详情失败');
    } catch (error) {
      console.error('获取视频详情失败:', error);
      return { success: false, error: error.message || '获取视频详情失败' };
    }
  };

  const listVideos = async (params = {}) => {
    try {
      const response = await axios.get('/api/video/list', { params });
      if (response.data.code === 0) {
        const items = Array.isArray(response.data.data) ? response.data.data : [];
        const counts = response.data.counts || null;
        return { success: true, data: items, counts };
      }
      throw new Error(response.data.msg || '获取视频列表失败');
    } catch (error) {
      console.error('获取视频列表失败:', error);
      return { success: false, error: error.message || '获取视频列表失败' };
    }
  };

  const getSubtitles = async (videoId, { lang = 'ai-zh', fmt = 'srt' } = {}) => {
    try {
      const response = await axios.get('/api/video/subtitles', {
        params: { video_id: videoId, lang, fmt },
        responseType: 'text'
      });
      // 字幕接口返回纯文本
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message || '获取字幕失败' };
    }
  };

  return {
    getVideoDetail,
    listVideos,
    getSubtitles,
  };
}



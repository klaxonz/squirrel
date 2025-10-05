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
        const payload = response.data.data || {};
        const items = Array.isArray(payload.data) ? payload.data : [];
        return { success: true, data: items };
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

  const getRelatedVideos = async (video, { pageSize = 20 } = {}) => {
    if (!video) return { success: true, data: [] };
    const collected = [];

    // 1) Try by subscription
    const primarySubId = video?.subscriptions?.[0]?.id;
    if (primarySubId) {
      const bySub = await listVideos({ page: 1, pageSize, sort_by: 'publish_date', subscription_id: primarySubId });
      if (bySub.success && Array.isArray(bySub.data)) collected.push(...bySub.data);
    }

    // 2) Fallback by site if empty or insufficient
    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length;
      const bySite = await listVideos({ page: 1, pageSize: remaining, sort_by: 'publish_date', site: video.site });
      if (bySite.success && Array.isArray(bySite.data)) collected.push(...bySite.data);
    }

    // 3) Unique by id and exclude current
    const unique = [];
    const seen = new Set();
    for (const item of collected) {
      if (!item || item.id === video.id) continue;
      if (seen.has(item.id)) continue;
      seen.add(item.id);
      unique.push(item);
      if (unique.length >= pageSize) break;
    }

    return { success: true, data: unique };
  };

  const getRandomVideo = async (params = {}) => {
    try {
      const response = await axios.get('/api/video/random', { params });
      if (response.data?.code === 0 && response.data?.data) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || '获取随机视频失败');
    } catch (error) {
      return { success: false, error: error.message || '获取随机视频失败' };
    }
  };

  const getVideoCounts = async (params = {}) => {
    try {
      const response = await axios.get('/api/video/counts', { params });
      if (response.data.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data.msg || '获取计数失败');
    } catch (error) {
      console.error('获取视频计数失败:', error);
      return { success: false, error: error.message || '获取视频计数失败' };
    }
  };

  return {
    getVideoDetail,
    listVideos,
    getSubtitles,
    getRelatedVideos,
    getRandomVideo,
    getVideoCounts,
  };
}



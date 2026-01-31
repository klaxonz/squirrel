import { get } from '../utils/request'

export function useVideoApi() {
  const getVideoDetail = async (videoId) => {
    return get('/api/video/detail', { video_id: videoId })
  }

  const listVideos = async (params = {}) => {
    const { data, error } = await get('/api/video/list', params)
    const items = Array.isArray(data?.data) ? data.data : []
    return { data: items, error }
  }

  const getSubtitles = async (videoId, { lang = 'ai-zh', fmt = 'srt' } = {}) => {
    return get(
      '/api/video/subtitles',
      { video_id: videoId, lang, fmt },
      { responseType: 'text' }
    )
  }

  const getRelatedVideos = async (video, { pageSize = 20 } = {}) => {
    if (!video) return { data: [], error: null }
    const collected = [];

    // 1) Try by subscription
    const primarySubId = video?.subscriptions?.[0]?.id;
    if (primarySubId) {
      const bySub = await listVideos({ page: 1, pageSize, sort_by: 'publish_date', subscription_id: primarySubId });
      if (!bySub.error && Array.isArray(bySub.data)) collected.push(...bySub.data);
    }

    // 2) Fallback by site if empty or insufficient
    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length;
      const bySite = await listVideos({ page: 1, pageSize: remaining, sort_by: 'publish_date', site: video.site });
      if (!bySite.error && Array.isArray(bySite.data)) collected.push(...bySite.data);
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

    return { data: unique, error: null }
  }

  const getRandomVideo = async (params = {}) => {
    return get('/api/video/random', params)
  }

  const getVideoCounts = async (params = {}) => {
    return get('/api/video/counts', params)
  }

  return {
    getVideoDetail,
    listVideos,
    getSubtitles,
    getRelatedVideos,
    getRandomVideo,
    getVideoCounts,
  };
}



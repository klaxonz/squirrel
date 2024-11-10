import { ref } from 'vue';
import axios from '../utils/axios';

export function useVideoHistory() {
  const isLoading = ref(false);
  const error = ref(null);

  const updateWatchHistory = async (videoId, channelId, currentTime, duration) => {
    try {
      await axios.post('/api/video-history/update', {
        video_id: videoId,
        channel_id: channelId,
        watch_duration: Math.floor(currentTime),
        last_position: Math.floor(currentTime),
        total_duration: Math.floor(duration)
      });
    } catch (err) {
      console.error('Failed to update watch history:', err);
    }
  };

  const getWatchHistory = async (page = 1, pageSize = 20) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await axios.get('/api/video-history/list', {
        params: { page, pageSize }
      });
      
      if (response.data.code === 0) {
        return response.data.data;
      }
      throw new Error(response.data.msg || '获取观看历史失败');
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const clearHistory = async (videoIds = []) => {
    try {
      await axios.post('/api/video-history/clear', { video_ids: videoIds });
    } catch (err) {
      console.error('Failed to clear watch history:', err);
      throw err;
    }
  };

  return {
    isLoading,
    error,
    updateWatchHistory,
    getWatchHistory,
    clearHistory
  };
} 
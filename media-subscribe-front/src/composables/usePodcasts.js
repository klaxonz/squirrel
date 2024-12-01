import { ref } from 'vue';
import axios from '../utils/axios';

export function usePodcasts() {
  const podcasts = ref([]);
  const loading = ref(false);
  const error = ref(null);
  const page = ref(1);
  const hasMore = ref(true);

  const fetchPodcasts = async (searchQuery = '') => {
    if (loading.value || !hasMore.value) return;
    
    loading.value = true;
    try {
      const response = await axios.get('/api/podcasts/channels', {
        params: {
          page: page.value,
          search: searchQuery,
          limit: 20
        }
      });
      
      const { items: newPodcasts } = response.data;
      podcasts.value = [...podcasts.value, ...newPodcasts];
      hasMore.value = response.data.has_more;
      page.value++;
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const resetPodcasts = () => {
    podcasts.value = [];
    page.value = 1;
    hasMore.value = true;
    error.value = null;
  };

  const fetchListening = async () => {
    try {
      const response = await axios.get('/api/podcasts/listening');
      return response.data;
    } catch (err) {
      console.error('Failed to fetch listening podcasts:', err);
      return [];
    }
  };

  const updatePlayProgress = async (episodeId, position, duration) => {
    try {
      await axios.post(`/api/podcasts/episodes/${episodeId}/play`, {
        position,
        duration
      });
    } catch (err) {
      console.error('Failed to update play progress:', err);
    }
  };

  return {
    podcasts,
    loading,
    error,
    hasMore,
    fetchPodcasts,
    resetPodcasts,
    fetchListening,
    updatePlayProgress
  };
} 
import { ref } from 'vue';
import { useVideoApi } from './useVideoApi';

export default function useRelatedVideos(sourceVideo) {
  const relatedVideos = ref([]);
  const loadingRelated = ref(false);
  const { getRelatedVideos } = useVideoApi();

  const fetchRelatedVideos = async () => {
    if (!sourceVideo.value) return;
    loadingRelated.value = true;
    try {
      const { data, error } = await getRelatedVideos(sourceVideo.value, { pageSize: 20 });
      relatedVideos.value = !error ? (data || []) : [];
    } finally {
      loadingRelated.value = false;
    }
  };

  return {
    relatedVideos,
    loadingRelated,
    fetchRelatedVideos,
  };
}



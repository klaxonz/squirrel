import { ref } from 'vue';
import { useVideoApi } from './useVideoApi';

export default function useRelatedVideos(sourceVideo) {
  const relatedVideos = ref([]);
  const loadingRelated = ref(false);
  const { listVideos } = useVideoApi();

  const fetchRelatedVideos = async () => {
    if (!sourceVideo.value) return;
    loadingRelated.value = true;
    try {
      const primarySubId = sourceVideo.value?.subscriptions?.[0]?.id;
      const params = { page: 1, pageSize: 20, sort_by: 'publish_date' };
      if (primarySubId) {
        params.subscription_id = primarySubId;
      } else if (sourceVideo.value?.site) {
        params.site = sourceVideo.value.site;
      }
      const { success, data } = await listVideos(params);
      const items = success ? data : [];
      relatedVideos.value = items.filter(v => v.id !== sourceVideo.value.id).slice(0, 20);
    } catch (e) {
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



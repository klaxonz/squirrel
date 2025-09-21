import { ref, computed } from 'vue';
import { get } from '../utils/request';

export default function useLatestVideos(initial = {}) {
  // Instance-scoped state to avoid cross-view interference
  const videos = ref([]);
  const loading = ref(false);
  const allLoaded = ref(false);
  const error = ref(null);
  const activeTab = ref(initial.activeTab ?? 'unread');
  const videoCounts = ref({ all: 0, unread: 0, read: 0, preview: 0, liked: 0, later: 0 });
  const currentPage = ref(1);
  const searchQuery = ref(initial.searchQuery ?? '');
  const isResetting = ref(false);
  const subscriptionId = ref(initial.subscriptionId ?? null);
  const sortBy = ref(initial.sortBy ?? 'publish_date');
  const nsfw = ref(initial.nsfw ?? 'all');
  const site = ref(initial.site);

  const category = computed(() => (activeTab.value === 'all' ? undefined : activeTab.value));

  // Ensure only most recent in-flight request mutates state
  let requestToken = 0;

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return;
    loading.value = true;

    const pageSize = 50;
    const currentToken = ++requestToken;

    const { data, error: requestError } = await get('/api/video/list', {
      page: currentPage.value,
      pageSize,
      query: searchQuery.value || '',
      subscription_id: subscriptionId.value,
      category: category.value,
      sort_by: sortBy.value,
      nsfw: nsfw.value,
      site: site.value,
    });

    // If a newer request started, ignore this response
    if (currentToken !== requestToken) {
      loading.value = false;
      return;
    }

    if (requestError) {
      error.value = requestError;
      loading.value = false;
      return;
    }

    const newVideos = (data?.data || []).map((video) => ({
      ...video,
      is_read: video.is_read ?? false,
      isPlaying: false,
      video_url: null,
    }));

    videos.value =
      currentPage.value === 1
        ? newVideos
        : [
            ...videos.value,
            ...newVideos.filter((video) => !videos.value.some((existing) => existing.id === video.id)),
          ];

    currentPage.value++;
    allLoaded.value = newVideos.length < pageSize;
    loading.value = false;

    if (data?.counts) {
      videoCounts.value = data.counts;
      return data.counts;
    }
  };

  const resetAndReload = async () => {
    isResetting.value = true;
    currentPage.value = 1;
    allLoaded.value = false;
    error.value = null;
    try {
      await loadMore();
    } finally {
      isResetting.value = false;
    }
  };

  return {
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    videoCounts,
    handleSearch: resetAndReload,
    refresh: resetAndReload,
    loadMore,
    searchQuery,
    subscriptionId,
    sortBy,
    nsfw,
    site,
    isResetting,
  };
}

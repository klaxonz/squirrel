import { ref, computed, watch } from 'vue';
import { getVideoCounts, getVideoList } from '../api/video'

export default function useLatestVideos(initial = {}) {
  // Instance-scoped state to avoid cross-view interference
  const videos = ref([]);
  const loading = ref(false);
  const allLoaded = ref(false);
  const error = ref(null);
  const activeTab = ref(initial.activeTab ?? 'unread');
  const videoCounts = ref({ all: 0, unread: 0, read: 0, preview: 0, liked: 0, later: 0 });
  const countsLoading = ref(false);
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
  let countsRequestToken = 0;

  // 异步加载视频计数（独立接口，不阻塞列表）
  const loadVideoCounts = async () => {
    countsLoading.value = true;
    const currentToken = ++countsRequestToken;

    const { data, error: requestError } = await getVideoCounts({
      query: searchQuery.value || '',
      subscription_id: subscriptionId.value,
      nsfw: nsfw.value,
      site: site.value,
    });

    // If a newer request started, ignore this response
    if (currentToken !== countsRequestToken) {
      countsLoading.value = false;
      return;
    }

    if (!requestError && data) {
      videoCounts.value = data;
    }
    
    countsLoading.value = false;
    return data;
  };

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return;
    loading.value = true;

    const pageSize = 50;
    const currentToken = ++requestToken;

    // 不再请求 counts，提升列表加载速度
    const { data, error: requestError } = await getVideoList({
      page: currentPage.value,
      pageSize,
      query: searchQuery.value || '',
      subscription_id: subscriptionId.value,
      category: category.value,
      sort_by: sortBy.value,
      nsfw: nsfw.value,
      site: site.value,
    });

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

    if (currentPage.value === 1) {
      const seen = new Set();
      videos.value = newVideos.filter(video => {
        if (seen.has(video.id)) {
          return false;
        }
        seen.add(video.id);
        return true;
      });
    } else {
      const existingIds = new Set(videos.value.map(v => v.id));
      const uniqueNewVideos = newVideos.filter(video => {
        if (existingIds.has(video.id)) {
          return false;
        }
        return true;
      });
      videos.value = [...videos.value, ...uniqueNewVideos];
    }

    currentPage.value++;
    allLoaded.value = newVideos.length < pageSize;
    loading.value = false;

    if (currentPage.value === 2) {
      loadVideoCounts();
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

  // 监听筛选条件变化，重新加载 counts
  watch([subscriptionId, searchQuery, nsfw, site], () => {
    if (currentPage.value > 1) {
      loadVideoCounts();
    }
  });

  return {
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    videoCounts,
    countsLoading,
    handleSearch: resetAndReload,
    refresh: resetAndReload,
    loadMore,
    loadVideoCounts,
    searchQuery,
    subscriptionId,
    sortBy,
    nsfw,
    site,
    isResetting,
  };
}

import { ref, computed } from 'vue';
import { get } from '../utils/request';

const videoContainer = ref(null);
const videos = ref([]);
const loading = ref(false);
const allLoaded = ref(false);
const error = ref(null);
const activeTab = ref('unread');
const videoCounts = ref({ all: 0, unread: 0, read: 0, preview: 0, liked: 0});
const currentPage = ref(1);
const searchQuery = ref('');
const isResetting = ref(false);
const subscriptionId = ref(null);
const sortBy = ref('publish_date');
const nsfw = ref('all');
const site = ref();

export default function useLatestVideos() {
  const tabs = [
    { label: '全部', value: 'all' },
    { label: '未读', value: 'unread' },
    { label: '已读', value: 'read' },
    { label: '预告', value: 'preview' },
    { label: '喜欢', value: 'liked' },
  ];

  const category = computed(() => activeTab.value === 'all' ? undefined : activeTab.value);

  const tabsWithCounts = computed(() => 
    tabs.map(tab => ({
      ...tab,
      count: videoCounts.value[tab.value]
    }))
  );

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return;
    loading.value = true;

    const pageSize = 50;
    const siteParam = site.value;
    const queryParam = searchQuery.value || '';

    const { data, error: requestError } = await get('/api/video/list', {
      page: currentPage.value,
      pageSize,
      query: queryParam,
      subscription_id: subscriptionId.value,
      category: category.value,
      sort_by: sortBy.value,
      nsfw: nsfw.value,
      site: siteParam
    });

    if (requestError) {
      error.value = requestError;
      loading.value = false;
      return;
    }

    const newVideos = data.data.map(video => ({
      ...video,
      is_read: video.is_read ?? false,
      isPlaying: false,
      video_url: null
    }));
    
    videos.value = currentPage.value === 1 
      ? newVideos 
      : [...videos.value, ...newVideos.filter(video => 
          !videos.value.some(v => v.id === video.id)
        )];
    
    currentPage.value++;
    allLoaded.value = newVideos.length < pageSize;
    loading.value = false;
    
    if (data.counts) {
      videoCounts.value = data.counts;
      return data.counts;
    }
  };

  const handleScroll = (event) => {
    const { scrollTop, clientHeight, scrollHeight } = event.target;
    // 增加预加载阈值，从300px增加到800px，让用户提前加载更多内容
    if (scrollHeight - (scrollTop + clientHeight) <= 800 && !loading.value && !allLoaded.value) {
      loadMore();
    }
  };

  const resetAndReload = () => {
    isResetting.value = true;
    currentPage.value = 1;
    allLoaded.value = false;
    error.value = null;
    loadMore().finally(() => {
      isResetting.value = false;
    });
  };

  return {
    videoContainer,
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    tabs,
    videoCounts,
    tabsWithCounts,
    handleSearch: resetAndReload,
    loadMore,
    handleScroll,
    searchQuery,
    subscriptionId,
    sortBy,
    nsfw,
    site,
    isResetting
  };
}

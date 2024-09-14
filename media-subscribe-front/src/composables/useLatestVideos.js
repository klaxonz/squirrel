import { ref, computed, watch } from 'vue';
import axios from '../utils/axios';

export default function useLatestVideos() {
  const videoContainer = ref(null);
  const videos = ref({
    all: [],
    unread: [],
    read: []
  });
  const loading = ref(false);
  const allLoaded = ref(false);
  const error = ref(null);
  const activeTab = ref('all');
  const tabContents = ref({ all: null, unread: null, read: null });
  const tabs = [
    { label: '全部', value: 'all' },
    { label: '未读', value: 'unread' },
    { label: '已读', value: 'read' },
  ];
  const videoCounts = ref({ all: 0, unread: 0, read: 0 });
  const observers = ref({});
  const videoRefs = ref({});
  const loadTrigger = ref(null);
  const refreshHeight = ref(0);
  const isRefreshing = ref(false);
  const showRefreshIndicator = ref(false);
  const currentPage = ref(1);
  const searchQuery = ref('');
  const isResetting = ref(false);

  const tabsWithCounts = computed(() => {
    return tabs.map(tab => ({
      ...tab,
      count: videoCounts.value[tab.value]
    }));
  });

  const isReadPage = computed(() => activeTab.value === 'read');

  const handleSearch = (query) => {
    searchQuery.value = query;
    resetAndReload();
  };

  const loadMore = async () => {
    if (loading.value || allLoaded.value || isRefreshing.value) return;

    loading.value = true;
    try {
      const response = await axios.get('/api/channel-video/list', {
        params: {
          page: currentPage.value,
          pageSize: 10,
          query: searchQuery.value,
          read_status: activeTab.value === 'all' ? null : activeTab.value
        }
      });

      if (response.data.code === 0) {
        const newVideos = response.data.data.data.map(video => ({
          ...video,
          isPlaying: false,
          video_url: null
        }));
        videos.value[activeTab.value] = [...videos.value[activeTab.value], ...newVideos];
        currentPage.value++;
        allLoaded.value = newVideos.length < 10;
        videoCounts.value = response.data.data.counts;
      } else {
        throw new Error(response.data.msg || '获取视频列表失败');
      }
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const refreshContent = async () => {
    if (isRefreshing.value) return;
    
    isRefreshing.value = true;
    loading.value = true;
    try {
      currentPage.value = 1;
      const response = await axios.get('/api/channel-video/list', {
        params: {
          page: 1,
          pageSize: 10,
          query: searchQuery.value,
          read_status: activeTab.value === 'all' ? null : activeTab.value
        }
      });

      if (response.data.code === 0) {
        const newVideos = response.data.data.data.map(video => ({
          ...video,
          isPlaying: false,
          video_url: null
        }));
        videos.value[activeTab.value] = newVideos;
        allLoaded.value = newVideos.length < 10;
        videoCounts.value = response.data.data.counts;
      } else {
        throw new Error(response.data.msg || '刷新视频列表失败');
      }
    } catch (error) {
      console.error('Error refreshing content:', error);
      error.value = error.message;
    } finally {
      loading.value = false;
      isRefreshing.value = false;
    }
  };

  const resetAndReload = () => {
    isResetting.value = true;
    videos.value[activeTab.value] = [];
    currentPage.value = 1;
    allLoaded.value = false;
    error.value = null;
    loadMore().then(() => {
      isResetting.value = false;
    });
  };

  const handleScroll = (event) => {
    const scrollContent = event.target;
    const containerRect = scrollContent.getBoundingClientRect();
    if (loadTrigger.value && loadTrigger.value.getBoundingClientRect) {
      const triggerRect = loadTrigger.value.getBoundingClientRect();
      if (triggerRect.top <= containerRect.bottom + 100) {
        loadMore();
      }
    }
  };

  const scrollToTopAndRefresh = () => {
    if (videoContainer.value) {
      videoContainer.value.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
    refreshContent();
  };

  const setLoadTrigger = (el) => {
    if (el) loadTrigger.value = el;
  };

  watch(activeTab, () => {
    resetAndReload();
  });

  return {
    videoContainer,
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    tabContents,
    tabs,
    videoCounts,
    tabsWithCounts,
    isReadPage,
    observers,
    videoRefs,
    loadTrigger,
    refreshHeight,
    isRefreshing,
    showRefreshIndicator,
    handleSearch,
    loadMore,
    refreshContent,
    handleScroll,
    scrollToTopAndRefresh,
    setLoadTrigger,
    isResetting,
  };
}
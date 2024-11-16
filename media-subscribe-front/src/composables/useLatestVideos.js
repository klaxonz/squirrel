import { ref, computed, watch } from 'vue';
import axios from '../utils/axios';

export default function useLatestVideos() {
  const videoContainer = ref(null);
  const videos = ref([]);
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
  const currentPage = ref(1);
  const searchQuery = ref('');
  const isResetting = ref(false);
  const channelId = ref('');
  const readStatus = computed(() => {
    if (activeTab.value === 'all') {
      return undefined;
    } else {
      return activeTab.value;
    }
  });
  const sortBy = ref('uploaded_at')

  const tabsWithCounts = computed(() => {
    return tabs.map(tab => ({
      ...tab,
      count: videoCounts.value[tab.value]
    }));
  });

  const handleSearch = () => {
    resetAndReload();
  };

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return;

    loading.value = true;
    try {
      const pageSize = currentPage.value === 1 ? 30 : 30;
      const response = await axios.get('/api/channel-video/list', {
        params: {
          page: currentPage.value,
          pageSize: pageSize,
          query: searchQuery.value,
          channel_id: channelId.value,
          read_status: readStatus.value,
          sort_by: sortBy.value
        }
      });

      if (response.data.code === 0) {
        const newVideos = response.data.data.data.map(video => ({
          ...video,
          is_read: video.is_read ?? false,
          isPlaying: false,
          video_url: null
        }));
        
        if (currentPage.value === 1) {
          videos.value = newVideos;
        } else {
          videos.value = [...videos.value, ...newVideos];
        }
        
        currentPage.value++;
        allLoaded.value = newVideos.length < pageSize;
        
        if (response.data.data.counts) {
          videoCounts.value = response.data.data.counts;
          return response.data.data.counts;
        }
      } else {
        throw new Error(response.data.msg || '获取视频列表失败');
      }
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const handleScroll = (event, channelId, read_status, keyword) => {
    const scrollContent = event.target;
    const scrollPosition = scrollContent.scrollTop + scrollContent.clientHeight;
    const scrollHeight = scrollContent.scrollHeight;

    if (scrollHeight - scrollPosition <= 300 && !loading.value && !allLoaded.value) {
      loadMore();
    }
  };

  const resetAndReload = (readStatus) => {
    isResetting.value = true;
    videos.value = [];
    currentPage.value = 1;
    allLoaded.value = false;
    error.value = null;
    loadMore(readStatus).then(() => {
      isResetting.value = false;
    });
  };

  const setLoadTrigger = (el) => {
    if (el) loadTrigger.value = el;
  };


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
    observers,
    videoRefs,
    loadTrigger,
    handleSearch,
    loadMore,
    handleScroll,
    setLoadTrigger,
    isResetting,
    searchQuery,
    channelId,
    sortBy
  };
}

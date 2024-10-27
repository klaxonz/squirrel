<template>
  <div class="download-tasks bg-[#0f0f0f] min-h-screen text-white mx-4">
    <!-- 搜索框 -->
    <SearchBar @search="handleSearch"/>

    <!-- 标签栏 -->
    <TabBar
      v-model="activeTab"
      :tabs="tabs"
    />

    <!-- 任务列表 -->
    <div class="task-container space-y-4" ref="taskContainer" @scroll="handleScroll">
      <div v-for="task in tasks" :key="task.id" class="task-item bg-[#272727] rounded-lg overflow-hidden">
        <div class="flex p-4">
          <img :src="task.thumbnail" :alt="task.title" referrerpolicy="no-referrer" class="w-40 h-24 object-cover rounded mr-4">
          <div class="flex-grow">
            <h2 class="task-title text-lg font-semibold mb-2">{{ task.title }}</h2>
            <p class="task-channel text-sm text-gray-400">{{ task.channel_name }}</p>
            <div class="mt-2 flex items-center justify-between">
              <span class="task-status text-sm font-medium" :class="getStatusClass(task.status)">
                {{ getStatusText(task) }}
              </span>
              <div class="text-sm text-gray-400">
                {{ formatSize(task.total_size) }}
              </div>
            </div>

            <!-- 进度条 -->
            <div v-if="task.status === 'DOWNLOADING'" class="mt-2">
              <div class="bg-gray-700 rounded-full h-2">
                <div class="bg-red-500 h-2 rounded-full" :style="{ width: `${task.percent}%` }"></div>
              </div>
              <div class="flex justify-between text-xs text-gray-400 mt-1">
                <span>{{ task.percent }}%</span>
                <span>{{ task.speed }}</span>
                <span>剩余: {{ task.eta }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="px-4 py-2 bg-[#1f1f1f] flex justify-end space-x-2">
          <button v-if="task.status === 'FAILED'" @click="retryTask(task.id)" class="btn btn-red">重试</button>
          <button v-if="task.status === 'DOWNLOADING'" @click="pauseTask(task.id)" class="btn btn-gray">暂停</button>
          <button v-if="task.status === 'COMPLETED'" @click="playVideo(task.id)" class="btn btn-red">播放</button>
          <button @click="deleteTask(task.id)" class="btn btn-gray">删除</button>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-4">
        <p class="text-gray-400">加载中...</p>
      </div>

      <!-- 加载完成状态 -->
      <div v-if="!loading && !hasMore" class="text-center py-4">
        <p class="text-gray-400">没有更多任务了</p>
      </div>

      <div ref="loadTrigger" class="h-1"></div>
    </div>

    <!-- 简化的视频播放器模态框 -->
    <div v-if="showVideoPlayer" class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div class="bg-[#0f0f0f] rounded-lg overflow-hidden w-full max-w-4xl shadow-2xl">
        <div class="relative">
          <video
            ref="videoPlayer"
            :src="currentVideoUrl"
            controls
            autoplay
            class="w-full aspect-video"
          >
            Your browser does not support the video tag.
          </video>
          <button @click="closeVideoPlayer" class="absolute top-4 right-4 text-white hover:text-gray-300 focus:outline-none">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import axios from '../utils/axios';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';

const tasks = ref([]);
const page = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const hasMore = ref(true);
const taskContainer = ref(null);
const showVideoPlayer = ref(false);
const currentVideoUrl = ref('');
const videoPlayer = ref(null);

const eventSource = ref(null);
const latestTaskId = ref(0);
const newTaskEventSource = ref(null);

const activeTab = ref('all');
const tabs = [
  { label: '全部', value: 'all' },
  { label: '下载中', value: 'downloading' },
  { label: '已完成', value: 'completed' },
  { label: '已暂停', value: 'paused' }, // 新增的已暂停标签
  { label: '失败', value: 'failed' },
];

const setupEventSource = () => {
  if (eventSource.value) {
    eventSource.value.close();
  }

  const taskIds = tasks.value.map(task => task.id).join(',');
  eventSource.value = new EventSource(`/api/task/progress?task_ids=${taskIds}`);

  eventSource.value.onmessage = (event) => {
    const data = JSON.parse(event.data);
    let shouldRefetch = false;
    data.forEach(taskData => {
      console.log('Received task data:', taskData);
      const taskIndex = tasks.value.findIndex(task => task.id === taskData.task_id);
      if (taskIndex !== -1) {
        const oldStatus = tasks.value[taskIndex].status;
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...taskData, percent: parseFloat(taskData.percent) };
        if (oldStatus === 'DOWNLOADING' && taskData.status === 'COMPLETED') {
          shouldRefetch = true;
        }
      }
    });
    if (shouldRefetch) {
      resetAndFetchTasks();
    }
  };

  eventSource.value.onerror = (error) => {
    console.error('EventSource error:', error);
    eventSource.value.close();
  };
};

const setupNewTaskEventSource = () => {
  if (newTaskEventSource.value) {
    newTaskEventSource.value.close();
  }

  newTaskEventSource.value = new EventSource(`/api/task/new_task_notification?latest_task_id=${latestTaskId.value}`);

  newTaskEventSource.value.onmessage = (event) => {
    const newTasks = JSON.parse(event.data);
    if (newTasks.length > 0) {
      tasks.value = [...newTasks, ...tasks.value];
      latestTaskId.value = Math.max(...newTasks.map(task => task.id));
      setupEventSource(); // Update the EventSource to include new task IDs
    }
  };

  newTaskEventSource.value.onerror = (error) => {
    console.error('New Task EventSource error:', error);
    newTaskEventSource.value.close();
  };
};

watch(latestTaskId, () => {
  setupNewTaskEventSource();
});

onMounted(() => {
  fetchTasks();
  setupEventSource();
  setupNewTaskEventSource();
});

onUnmounted(() => {
  if (eventSource.value) {
    eventSource.value.close();
  }
  if (newTaskEventSource.value) {
    newTaskEventSource.value.close();
  }
});

const fetchTasks = async () => {
  if (loading.value || !hasMore.value) return;
  
  loading.value = true;
  try {
    const response = await axios.get('/api/task/list', {
      params: {
        status: activeTab.value === 'all' ? '' : activeTab.value.toUpperCase(),
        page: page.value,
        pageSize: pageSize.value
      }
    });
    const newTasks = response.data.data.data;
    
    if (newTasks.length > 0) {
      const maxTaskId = Math.max(...newTasks.map(task => task.id));
      latestTaskId.value = Math.max(latestTaskId.value, maxTaskId);
    }
    
    tasks.value = [...tasks.value, ...newTasks];
    page.value++;
    hasMore.value = newTasks.length === pageSize.value;
    
    setupEventSource();
  } catch (error) {
    console.error('获取任务列表失败:', error);
  } finally {
    loading.value = false;
  }
};

const resetAndFetchTasks = () => {
  const scrollPosition = taskContainer.value ? taskContainer.value.scrollTop : 0;
  
  tasks.value = [];
  page.value = 1;
  hasMore.value = true;
  if (eventSource.value) {
    eventSource.value.close();
  }
  
  fetchTasks().then(() => {
    nextTick(() => {
      if (taskContainer.value) {
        taskContainer.value.scrollTop = scrollPosition;
      }
    });
  });
};

const retryTask = async (taskId) => {
  try {
    await axios.post('/api/task/retry', { task_id: taskId });
    resetAndFetchTasks();
  } catch (error) {
    console.error('重试任务失败:', error);
  }
};

const pauseTask = async (taskId) => {
  try {
    await axios.post('/api/task/pause', { task_id: taskId });
    resetAndFetchTasks();
  } catch (error) {
    console.error('暂停任务失败:', error);
  }
};

const deleteTask = async (taskId) => {
  if (confirm('确定要删除这个任务吗？')) {
    try {
      await axios.post('/api/task/delete', { task_id: taskId });
      resetAndFetchTasks();
    } catch (error) {
      console.error('删除任务失败:', error);
    }
  }
};

const playVideo = (taskId) => {
  const task = tasks.value.find(t => t.id === taskId);
  if (task) {
    currentVideoUrl.value = `/api/task/video/play/${taskId}`;
    showVideoPlayer.value = true;
    nextTick(() => {
      if (videoPlayer.value) {
        videoPlayer.value.focus();
      }
    });
  }
};

const closeVideoPlayer = () => {
  showVideoPlayer.value = false;
  if (videoPlayer.value) {
    videoPlayer.value.pause();
    videoPlayer.value.currentTime = 0;
  }
};

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const handleScroll = () => {
  const container = taskContainer.value;
  if (container) {
    const { scrollTop, clientHeight, scrollHeight } = container;
    if (scrollTop + clientHeight >= scrollHeight - 100) {
      fetchTasks();
    }
  }
};

const getStatusClass = (status) => {
  switch (status) {
    case 'PENDING':
      return 'text-yellow-600';
    case 'DOWNLOADING':
      return 'text-blue-600';
    case 'COMPLETED':
      return 'text-green-600';
    case 'FAILED':
      return 'text-red-600';
    case 'PAUSED':
      return 'text-gray-600';
    default:
      return 'text-gray-700';
  }
};

const getStatusText = (task) => {
  if (task.status === 'DOWNLOADING') {
    if (task.current_type) {
      return `下载中 (${task.current_type === 'video' ? '视频' : '音频'})`;
    } else {
      return '准备下载中...';
    }
  }
  if (task.status === 'COMPLETED') {
    return '已完成';
  }
  if (task.status === 'FAILED') {
    return '失败';
  }
  if (task.status === 'PAUSED') {
    return '已暂停';
  }
  if (task.status === 'PENDING') {
    return '等待中';
  }
  return task.status;
};

const handleSearch = (query) => {
  console.log('Search query:', query);
  // 实现搜索逻辑
};

watch(activeTab, (newTab) => {
  console.log('Active tab changed:', newTab);
  resetAndFetchTasks();
});

watch(tasks, (newTasks) => {
  console.log('Tasks updated:', newTasks);
}, { deep: true });
</script>

<style scoped>
.download-tasks {
  @apply min-h-full;
}

.task-container {
  height: calc(100vh - 130px); /* 恢复原有高度 */
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* Internet Explorer 10+ */
}

@media (min-width: 768px) {
  .task-container {
    height: calc(100vh - 90px); /* 恢复原有高度 */
  }
}

.task-container::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none; /* Chrome, Safari, Opera */
}

.task-item {
  @apply mt-3; /* 恢复为 mt-3 */
}

.task-title {
  @apply line-clamp-2 leading-tight;
}

.task-channel {
  @apply truncate;
}

.task-status {
  @apply inline-flex items-center;
}

.download-progress {
  @apply mt-2; /* 恢复为 mt-2 */
}

.progress-bar {
  @apply bg-gray-700 rounded-full h-2;
}

.progress-bar > div {
  @apply bg-red-500 h-2 rounded-full transition-all duration-300 ease-in-out;
}

.btn {
  @apply px-4 py-2 rounded-full text-sm font-medium transition duration-200 focus:outline-none focus:ring-2 focus:ring-opacity-50;
}

.btn-red {
  @apply bg-red-500 text-white hover:bg-red-600 focus:ring-red-500;
}

.btn-gray {
  @apply bg-gray-700 text-white hover:bg-gray-600 focus:ring-gray-500;
}

.btn + .btn {
  @apply ml-2;
}
</style>

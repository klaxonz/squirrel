<template>
  <div class="download-tasks bg-gray-100 min-h-screen flex flex-col">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 w-full flex-grow flex flex-col">
      <!-- 搜索栏 -->
      <div class="search-bar sticky top-0 bg-white z-10 p-4 shadow-sm">
        <div class="flex items-center max-w-3xl mx-auto relative">
          <select v-model="status" @change="resetAndFetchTasks" class="flex-grow h-10 px-4 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200">
            <option value="">全部状态</option>
            <option value="PENDING">等待中</option>
            <option value="DOWNLOADING">下载中</option>
            <option value="COMPLETED">已完成</option>
            <option value="FAILED">失败</option>
            <option value="PAUSED">已暂停</option>
          </select>
          <button 
            @click="resetAndFetchTasks"
            class="h-10 px-6 text-sm font-medium bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200"
          >
            筛选
          </button>
        </div>
      </div>

      <div class="task-container flex-grow overflow-y-auto" ref="taskContainer" @scroll="handleScroll">
        <div 
          v-for="task in tasks" 
          :key="task.id" 
          class="task-item bg-white shadow-sm rounded-lg overflow-hidden mb-4 p-4"
        >
          <div class="flex items-start mb-3">
            <img 
              :src="task.thumbnail" 
              :alt="task.title"
              referrerpolicy="no-referrer"
              class="w-24 h-16 object-cover rounded mr-4"
            >
            <div class="flex-grow">
              <h2 class="task-title text-base font-semibold text-gray-900 line-clamp-2 mb-1">{{ task.title }}</h2>
              <p class="task-channel text-sm text-gray-600 truncate">{{ task.channel_name }}</p>
            </div>
          </div>
          
          <!-- 进度信息 -->
          <div class="mt-2">
            <div class="flex items-center justify-between text-sm mb-1">
              <span class="task-status font-medium" :class="getStatusClass(task.status)">
                {{ getStatusText(task) }}
              </span>
            </div>
            
            <div v-if="task.status === 'DOWNLOADING'" class="download-progress">
              <div class="mb-2">
                <div class="progress-bar bg-gray-200 rounded-full h-2.5 mb-1">
                  <div 
                    class="bg-blue-600 h-2.5 rounded-full" 
                    :style="{ width: `${task.percent}%` }"
                  ></div>
                </div>
                <div class="flex justify-between text-xs text-gray-600">
                  <span>{{ task.percent }}%</span>
                  <span>{{ formatSize(task.downloaded_size) }} / {{ formatSize(task.total_size) }}</span>
                  <span>{{ task.speed }}</span>
                  <span>剩余: {{ task.eta }}</span>
                </div>
              </div>
            </div>
            
            <p v-if="task.status === 'FAILED'" class="text-sm text-red-600 mt-1">错误: {{ task.error_message }}</p>
          </div>
          
          <div class="mt-3 flex justify-between items-center">
            <div class="text-sm text-gray-600">
              重试次数: {{ task.retry }} 
            </div>
            <div class="text-sm text-gray-600">
              <span v-if="task.total_size" class="text-gray-600">
                {{ formatSize(task.total_size) }}
              </span>
            </div>
            <div>
              <button v-if="task.status === 'FAILED'" @click="retryTask(task.id)" class="btn btn-primary">重试</button>
              <button v-if="task.status === 'DOWNLOADING'" @click="pauseTask(task.id)" class="btn btn-secondary">暂停</button>
              <button v-if="task.status === 'COMPLETED'" @click="playVideo(task.id)" class="btn btn-primary">播放</button>
              <button @click="deleteTask(task.id)" class="btn btn-danger">删除</button>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-4">
          <p class="text-gray-600">加载中...</p>
        </div>

        <!-- 加载完成状态 -->
        <div v-if="!loading && !hasMore" class="text-center py-4">
          <p class="text-gray-600">没有更多任务了</p>
        </div>

        <!-- 添加一个用于触发加载的元素 -->
        <div ref="loadTrigger" class="h-1"></div>
      </div>
    </div>

    <!-- 视频播放器模态框 -->
    <div v-if="showVideoPlayer" class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div class="bg-gray-900 rounded-lg overflow-hidden w-full max-w-4xl shadow-2xl">
        <div class="relative">
          <video ref="videoPlayer" controls autoplay class="w-full aspect-video">
            <source :src="currentVideoUrl" type="video/mp4">
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

const tasks = ref([]);
const status = ref('');
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
        status: status.value,
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
    return '';
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

watch(tasks, (newTasks) => {
  console.log('Tasks updated:', newTasks);
}, { deep: true });
</script>

<style scoped>
.download-tasks {
  @apply min-h-full;
}

.task-container {
  height: calc(100vh - 130px); /* 120px (搜索栏) + 56px (底部导航栏) */
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* Internet Explorer 10+ */
}

@media (min-width: 768px) {
  .task-container {
    height: calc(100vh - 90px); /* 只考虑搜索栏的高度，因为导航栏在侧边 */
  }
}

.task-container::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none; /* Chrome, Safari, Opera */
}

.task-item {
  @apply mt-3;
}

.task-title {
  @apply line-clamp-2 leading-tight;
}

.task-channel {
  @apply truncate;
}

.search-bar {
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 10;
  padding: 1rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.search-bar select {
  border-right: none;
}

.search-bar button {
  border-left: none;
}

.search-bar select:focus,
.search-bar button:focus {
  box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5);
}

.task-status {
  @apply inline-flex items-center;
}

.download-progress {
  @apply mt-2;
}

.progress-bar {
  @apply bg-gray-200 rounded-full h-2.5;
}

.progress-bar > div {
  @apply bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-in-out;
}

.btn {
  @apply px-3 py-1 rounded text-sm font-medium transition duration-200 focus:outline-none focus:ring-2 focus:ring-opacity-50;
}

.btn-primary {
  @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500;
}

.btn-secondary {
  @apply bg-gray-500 text-white hover:bg-gray-600 focus:ring-gray-400;
}

.btn-danger {
  @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
}

.btn + .btn {
  @apply ml-2;
}
</style>
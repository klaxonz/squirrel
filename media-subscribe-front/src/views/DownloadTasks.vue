<template>
  <div class="download-tasks bg-gray-100 min-h-screen flex flex-col">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 w-full flex-grow flex flex-col">
      <!-- 搜索栏 -->
      <div class="search-bar sticky top-0 bg-white z-10 p-4 shadow-sm">
        <div class="flex items-center max-w-3xl mx-auto relative">
          <select v-model="status" @change="resetAndFetchTasks" class="flex-grow h-8 px-4 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200">
            <option value="">全部状态</option>
            <option value="PENDING">等待中</option>
            <option value="DOWNLOADING">下载中</option>
            <option value="COMPLETED">已完成</option>
            <option value="FAILED">失败</option>
            <option value="PAUSED">已暂停</option>
          </select>
          <button 
            @click="resetAndFetchTasks"
            class="h-8 px-6 text-sm font-medium bg-blue-500 text-white rounded-r-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-50 focus:ring-offset-2 transition duration-200"
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
                {{ task.status }}
              </span>
              <span v-if="task.total_size" class="text-gray-600">
                {{ formatSize(task.total_size) }}
              </span>
            </div>
            
            <div v-if="task.status === 'DOWNLOADING'" class="download-progress">
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
            
            <p v-if="task.status === 'FAILED'" class="text-sm text-red-500 mt-1">错误: {{ task.error_message }}</p>
          </div>
          
          <div class="mt-3 flex justify-between items-center">
            <div class="text-sm text-gray-600">
              重试次数: {{ task.retry }} 
            </div>
            <div>
              <button v-if="task.status === 'FAILED'" @click="retryTask(task.id)" class="bg-blue-500 text-white px-3 py-1 rounded mr-2 text-sm">重试</button>
              <button v-if="task.status === 'DOWNLOADING'" @click="pauseTask(task.id)" class="bg-yellow-500 text-white px-3 py-1 rounded mr-2 text-sm">暂停</button>
              <button v-if="task.status === 'COMPLETED'" @click="playVideo(task.id)" class="bg-green-500 text-white px-3 py-1 rounded mr-2 text-sm">播放</button>
              <button @click="deleteTask(task.id)" class="bg-red-500 text-white px-3 py-1 rounded text-sm">删除</button>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-4">
          <p>加载中...</p>
        </div>

        <!-- 加载完成状态 -->
        <div v-if="!loading && !hasMore" class="text-center py-4">
          <p>没有更多任务了</p>
        </div>

        <!-- 添加一个用于触发加载的元素 -->
        <div ref="loadTrigger" class="h-1"></div>
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

const eventSources = ref({});
const newTaskEventSource = ref(null);
const latestTaskId = ref(0);

const setupEventSource = (taskId) => {
  console.log(`Setting up EventSource for task ${taskId}`);
  if (eventSources.value[taskId]) {
    console.log(`EventSource for task ${taskId} already exists, skipping setup`);
    return;
  }
  
  console.log(`Setting up new EventSource for task ${taskId}`);
  const eventSource = new EventSource(`/api/task/progress/${taskId}`);
  
  eventSource.onmessage = (event) => {
    console.log(`Received progress for task ${taskId}:`, event.data);
    const data = JSON.parse(event.data);
    const taskIndex = tasks.value.findIndex(task => task.id === data.task_id);
    if (taskIndex !== -1) {
      const updatedTask = { ...tasks.value[taskIndex], ...data };
      tasks.value[taskIndex] = updatedTask;

      if (updatedTask.status !== 'DOWNLOADING') {
        closeEventSource(taskId);
        if (updatedTask.status === 'COMPLETED' || updatedTask.status === 'FAILED') {
          // 可能需要触发一些UI更新或通知
        }
      }
    }
  };

  eventSource.onerror = (error) => {
    console.error(`EventSource error for task ${taskId}:`, error);
    closeEventSource(taskId);
  };

  eventSources.value[taskId] = eventSource;
};

const closeEventSource = (taskId) => {
  if (eventSources.value[taskId]) {
    console.log(`Closing EventSource for task ${taskId}`);
    eventSources.value[taskId].close();
    delete eventSources.value[taskId];
  }
};

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
    
    // 更新最新的任务ID
    if (newTasks.length > 0) {
      const maxTaskId = Math.max(...newTasks.map(task => task.id));
      console.log('Updating latest task ID in fetchTasks from', latestTaskId.value, 'to', maxTaskId);
      latestTaskId.value = Math.max(latestTaskId.value, maxTaskId);
    }
    
    // 更新任务列表
    tasks.value = [...tasks.value, ...newTasks];
    page.value++;
    hasMore.value = newTasks.length === pageSize.value;
    
    // 设置或关闭 EventSource
    tasks.value.forEach(task => {
      if (task.status === 'DOWNLOADING') {
        setupEventSource(task.id);
      } else {
        closeEventSource(task.id);
      }
    });
    
    // 清理不再需要的 EventSource
    Object.keys(eventSources.value).forEach(taskId => {
      if (!tasks.value.some(task => task.id === parseInt(taskId) && task.status === 'DOWNLOADING')) {
        closeEventSource(parseInt(taskId));
      }
    });
    
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
  // 关闭所有现有的 EventSource 连接
  Object.keys(eventSources.value).forEach(taskId => closeEventSource(parseInt(taskId)));
  
  fetchTasks().then(() => {
    // 在下一个 tick 恢复滚动位置
    nextTick(() => {
      if (taskContainer.value) {
        taskContainer.value.scrollTop = scrollPosition;
      }
    });
  });
};

// 监听 status 变化
watch(status, resetAndFetchTasks);

const setupNewTaskNotification = () => {
  console.log('Setting up new task notification with latest task ID:', latestTaskId.value);
  if (newTaskEventSource.value) {
    console.log('Closing existing EventSource');
    newTaskEventSource.value.close();
  }

  newTaskEventSource.value = new EventSource(`/api/task/new_task_notification?latest_task_id=${latestTaskId.value}`);
  
  newTaskEventSource.value.onopen = (event) => {
    console.log('New task notification EventSource opened:', event);
  };

  newTaskEventSource.value.onmessage = (event) => {
    console.log('New task notification received:', event.data);
    try {
      const newTasks = JSON.parse(event.data);
      if (Array.isArray(newTasks)) {
        console.log('New tasks received:', newTasks);
        
        let shouldReconnect = false;
        
        newTasks.forEach(newTask => {
          if (newTask.id > latestTaskId.value) {
            latestTaskId.value = newTask.id;
            shouldReconnect = true;
          }
          
          const existingTaskIndex = tasks.value.findIndex(task => task.id === newTask.id);
          if (existingTaskIndex === -1) {
            // 如果任务不存在，添加到列表开头
            tasks.value.unshift(newTask);
          } else {
            // 如果任务已存在，更新现有任务
            tasks.value[existingTaskIndex] = { ...tasks.value[existingTaskIndex], ...newTask };
          }
          
          // 为新的下载中任务设置 EventSource
          if (newTask.status === 'DOWNLOADING') {
            setupEventSource(newTask.id);
          } else {
            closeEventSource(newTask.id);
          }
        });
        
        console.log('Updated latest task ID:', latestTaskId.value);
        
        if (shouldReconnect) {
          console.log('Reconnecting with new latest task ID');
          setupNewTaskNotification(); // 重新连接，传递新的 latestTaskId
        }
      }
    } catch (error) {
      console.error('Error parsing event data:', error);
    }
  };

  newTaskEventSource.value.addEventListener('heartbeat', (event) => {
    console.log('Heartbeat event received:', event.data);
  });

  newTaskEventSource.value.onerror = (error) => {
    console.error('New task notification error:', error);
    newTaskEventSource.value.close();
    // 添加重连逻辑
    setTimeout(() => {
      console.log('Attempting to reconnect...');
      setupNewTaskNotification();
    }, 5000);
  };
};

onMounted(async () => {
  console.log('Component mounted');
  await fetchTasks();
  console.log('Tasks fetched, setting up new task notification');
  setupNewTaskNotification();
});

onUnmounted(() => {
  if (newTaskEventSource.value) {
    newTaskEventSource.value.close();
  }
  Object.keys(eventSources.value).forEach(taskId => closeEventSource(parseInt(taskId)));
});

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
  window.open(`/api/task/video/play/${taskId}`, '_blank');
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
      return 'text-yellow-500';
    case 'DOWNLOADING':
      return 'text-blue-500';
    case 'COMPLETED':
      return 'text-green-500';
    case 'FAILED':
      return 'text-red-500';
    case 'PAUSED':
      return 'text-gray-500';
    default:
      return 'text-gray-700';
  }
};
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
  box-shadow: 0 0 0 0 rgba(111, 164, 248, 0.5);
}

/* 添加进度条样式 */
.bg-gray-200 {
  background-color: #edf2f7;
}

.bg-blue-600 {
  background-color: #3182ce;
}

.rounded-full {
  border-radius: 9999px;
}

.h-2.5 {
  height: 0.625rem;
}

.task-status {
  @apply inline-block py-0.5 rounded-full text-xs;
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
</style>
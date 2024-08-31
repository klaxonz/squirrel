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
          <div class="flex items-start">
            <img 
              :src="task.thumbnail" 
              :alt="task.title"
              referrerpolicy="no-referrer"
              class="w-24 h-16 object-cover rounded mr-4"
            >
            <div class="flex-grow">
              <h2 class="task-title text-base font-semibold text-gray-900 line-clamp-2 mb-1">{{ task.title }}</h2>
              <p class="task-channel text-sm text-gray-600 truncate mb-2">{{ task.channel_name }}</p>
              <div class="flex justify-between items-center">
                <div class="task-status text-sm font-medium" :class="getStatusClass(task.status)">
                  {{ task.status }}
                </div>
                <div class="text-sm text-gray-600">
                  文件大小: {{ formatSize(task.total_size) }}
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="task.status === 'DOWNLOADING'" class="mt-3">
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm text-gray-600">下载进度</span>
              <span class="text-sm text-gray-600">{{ task.percent }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5">
              <div class="bg-blue-600 h-2.5 rounded-full" :style="{ width: `${task.percent}%` }"></div>
            </div>
            <p class="text-sm text-gray-600 mt-1">
              {{ formatSize(task.downloaded_size) }} / {{ formatSize(task.total_size) }}
            </p>
            <p class="text-sm text-gray-600">速度: {{ task.speed }}</p>
            <p class="text-sm text-gray-600">剩余时间: {{ task.eta }}</p>
          </div>
          
          <p v-if="task.status === 'FAILED'" class="text-sm text-red-500 mt-2">错误: {{ task.error_message }}</p>
          
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
import { ref, onMounted, onUnmounted } from 'vue';
import axios from '../utils/axios';

const tasks = ref([]);
const status = ref('');
const page = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const hasMore = ref(true);
const taskContainer = ref(null);

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
    tasks.value.push(...newTasks);
    page.value++;
    hasMore.value = newTasks.length === pageSize.value;
  } catch (error) {
    console.error('获取任务列表失败:', error);
  } finally {
    loading.value = false;
  }
};

const resetAndFetchTasks = () => {
  tasks.value = [];
  page.value = 1;
  hasMore.value = true;
  fetchTasks();
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

onMounted(() => {
  fetchTasks();
  window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
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
  @apply inline-block px-2 py-1 rounded-full text-xs font-semibold;
}
</style>
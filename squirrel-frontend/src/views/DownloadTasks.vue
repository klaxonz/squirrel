<template>
  <div class="flex flex-col h-full">
    <div class="flex-none px-4 pt-2 pb-3">
      <!-- 标题 -->
      <h1 class="text-xl font-semibold mb-4">下载任务</h1>

      <!-- 标签栏 -->
      <div class="flex overflow-x-auto scrollbar-hide">
        <button 
          v-for="tab in tabs" 
          :key="tab.value"
          @click="activeTab = tab.value"
          class="px-3 py-1.5 rounded-full text-sm whitespace-nowrap mr-2"
          :class="[
            activeTab === tab.value 
              ? 'bg-white text-black' 
              : 'text-white bg-[#ffffff1a] hover:bg-[#ffffff26]'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="flex-1 overflow-y-auto px-4">
      <div class="space-y-3" ref="taskContainer" @scroll="handleScroll">
        <div v-for="task in tasks" 
             :key="task.id" 
             class="task-item bg-[#1f1f1f] hover:bg-[#272727] transition-colors duration-200 rounded-xl overflow-hidden">
          <div class="flex p-3">
            <!-- 缩略图容器 -->
            <div class="relative w-32 md:w-40 h-20 md:h-24 rounded-lg overflow-hidden flex-shrink-0">
              <img 
                :src="task.thumbnail" 
                :alt="task.title" 
                referrerpolicy="no-referrer" 
                class="w-full h-full object-cover"
              >
              <!-- 视频时长 -->
              <div v-if="task.duration" class="absolute bottom-1 right-1 px-1 py-0.5 text-xs bg-black bg-opacity-80 rounded">
                {{ formatDuration(task.duration) }}
              </div>
            </div>

            <!-- 信息区域 -->
            <div class="flex-grow ml-3 min-w-0">
              <h2 class="task-title text-[14px] md:text-[15px] font-medium leading-5 mb-1 line-clamp-2">{{ task.title }}</h2>
              <p class="task-channel text-[12px] md:text-[13px] text-[#aaa] mb-1">{{ task.channel_name }}</p>
              
              <!-- 状态和大小 -->
              <div class="flex items-center justify-between text-[12px] md:text-[13px] text-[#aaa]">
                <div class="flex items-center">
                  <span v-if="task.status === 'DOWNLOADING'" class="flex items-center text-[#aaa]">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                    正在下载
                  </span>
                  <span v-else-if="task.status === 'COMPLETED'" class="flex items-center text-[#00c853]">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    已完成
                  </span>
                  <span v-else-if="task.status === 'FAILED'" class="flex items-center text-[#f44336]">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                    下载失败
                  </span>
                  <span v-else-if="task.status === 'PAUSED'" class="flex items-center text-[#aaa]">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                    已暂停
                  </span>
                </div>
                <span>{{ formatSize(task.total_size) }}</span>
              </div>

              <!-- 进度条 -->
              <div v-if="task.status === 'DOWNLOADING'" class="mt-2">
                <div class="bg-[#3f3f3f] rounded-full h-1">
                  <div class="bg-[#f00] h-1 rounded-full transition-all duration-300" 
                       :style="{ width: `${task.percent}%` }">
                  </div>
                </div>
                <div class="flex justify-between text-[11px] md:text-[12px] text-[#aaa] mt-1">
                  <span>{{ task.percent }}%</span>
                  <span>{{ task.speed }}</span>
                  <span>剩余: {{ task.eta }}</span>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-start ml-2 md:ml-3">
              <button 
                v-if="task.status === 'COMPLETED'" 
                @click="playVideo(task.id)"
                class="p-1.5 md:p-2 hover:bg-[#ffffff1a] rounded-full transition-colors duration-200"
                title="播放"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                </svg>
              </button>
              <button 
                @click="deleteTask(task.id)"
                class="p-1.5 md:p-2 hover:bg-[#ffffff1a] rounded-full transition-colors duration-200 text-[#aaa] hover:text-white"
                title="删除"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-4">
          <p class="text-[#aaa]">加载中...</p>
        </div>

        <!-- 加载完成状态 -->
        <div v-if="!loading && !hasMore" class="text-center py-4">
          <p class="text-[#aaa]">没有更多任务了</p>
        </div>

        <div ref="loadTrigger" class="h-1"></div>
      </div>
    </div>

    <!-- 视频播放器模态框 -->
    <div v-if="showVideoPlayer" class="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <div class="w-full max-w-4xl">
        <div class="relative">
          <video
            ref="videoPlayer"
            :src="currentVideoUrl"
            controls
            autoplay
            class="w-full aspect-video rounded-lg"
          >
            Your browser does not support the video tag.
          </video>
          <button 
            @click="closeVideoPlayer" 
            class="absolute -top-8 right-0 text-white hover:text-gray-300 focus:outline-none"
          >
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
import { createApp } from 'vue';
import Toast from '../components/Toast.vue';

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
  { label: '已暂停', value: 'paused' },
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
      // 更新最新任务ID
      latestTaskId.value = Math.max(...newTasks.map(task => task.id));
      
      // 检查是否需要重新获取任务列表
      const shouldRefetch = newTasks.some(newTask => {
        // 检查新任务是否符合当前标签页的状态过滤条件
        const matchesFilter = activeTab.value === 'all' || 
                            newTask.status.toLowerCase() === activeTab.value.toLowerCase();
        
        // 检查新任务是否已经存在于列表中
        const isDuplicate = tasks.value.some(existingTask => existingTask.id === newTask.id);
        
        return matchesFilter && !isDuplicate;
      });

      if (shouldRefetch) {
        resetAndFetchTasks();
      }
    }
  };

  newTaskEventSource.value.onerror = (error) => {
    console.error('New Task EventSource error:', error);
    newTaskEventSource.value.close();
    // 可以添加重连逻辑
    setTimeout(setupNewTaskEventSource, 5000);
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

const resetAndFetchTasks = (() => {
  let timeout;
  return () => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => {
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
    }, 300); // 300ms 的防抖延迟
  };
})();

const retryTask = async (taskId) => {
  try {
    await axios.post('/api/task/retry', { task_id: taskId });
    showToast('任务已重试');
    resetAndFetchTasks();
  } catch (error) {
    console.error('重试任务失败:', error);
    showToast('重试任务失败', 'error');
  }
};

const pauseTask = async (taskId) => {
  try {
    await axios.post('/api/task/pause', { task_id: taskId });
    showToast('任务已暂停');
    resetAndFetchTasks();
  } catch (error) {
    console.error('暂停任务失败:', error);
    showToast('暂停任务失败', 'error');
  }
};

const deleteTask = async (taskId) => {
  if (confirm('确定要删除这个任务吗？')) {
    try {
      await axios.post('/api/task/delete', { task_id: taskId });
      showToast('任务已删除');
      resetAndFetchTasks();
    } catch (error) {
      console.error('删除任务失败:', error);
      showToast('删除任务失败', 'error');
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
  } else {
    showToast('无法播放视频', 'error');
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
  const classes = {
    'DOWNLOADING': 'text-[#3ea6ff] bg-[#3ea6ff1a]',
    'COMPLETED': 'text-[#00c853] bg-[#00c8531a]',
    'FAILED': 'text-[#f44336] bg-[#f443361a]',
    'PAUSED': 'text-[#aaa] bg-[#aaaaaa1a]'
  };
  return classes[status] || 'text-[#aaa] bg-[#aaaaaa1a]';
};

const getStatusText = (task) => {
  const statusMap = {
    'DOWNLOADING': '正在下载',
    'COMPLETED': '已完成',
    'FAILED': '下载失败',
    'PAUSED': '已暂停'
  };
  return statusMap[task.status] || task.status;
};

const handleSearch = (query) => {
  console.log('Search query:', query);
  // 实现搜索逻辑
};

watch(activeTab, (newTab) => {
  resetAndFetchTasks();
});

watch(tasks, (newTasks) => {
}, { deep: true });

// 添加时长格式化函数
const formatDuration = (seconds) => {
  if (!seconds) return '';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const showToast = (message, type = 'success') => {
  const toast = createApp(Toast, {
    message,
    type,
    duration: 3000,
  });
  const mountNode = document.createElement('div');
  document.body.appendChild(mountNode);
  toast.mount(mountNode);
  
  setTimeout(() => {
    document.body.removeChild(mountNode);
  }, 3000);
};
</script>

<style scoped>
/* 确保图片加载时保持比例 */
.task-item img {
  aspect-ratio: 16 / 9;
}

/* 添加平滑过渡效果 */
.task-item {
  transition: background-color 0.2s ease;
}

/* 隐藏滚动条但保持功能 */
.scrollbar-hide,
.overflow-y-auto,
.overflow-x-auto {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.scrollbar-hide::-webkit-scrollbar,
.overflow-y-auto::-webkit-scrollbar,
.overflow-x-auto::-webkit-scrollbar {
  display: none; /* Chrome, Safari and Opera */
  width: 0;
  height: 0;
}
</style>

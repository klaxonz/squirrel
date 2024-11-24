<template>
  <div v-if="isOpen" 
       :class="[
         'fixed z-50 bg-black transition-all duration-300',
         isMinimized ? 'shadow-lg rounded-lg overflow-hidden' : 'inset-0',
         isDragging ? 'dragging select-none' : '',
         resizeState.isResizing ? 'resizing select-none' : ''
       ]"
       :style="miniPlayerStyle"
       @mousedown="startDrag"
       @keydown.esc="close" 
       tabindex="0"
  >
    <template v-if="isMinimized">
      <!-- 左边缘 -->
      <div class="resize-edge resize-w" @mousedown.stop="startResize('w')"></div>
      <!-- 右边缘 -->
      <div class="resize-edge resize-e" @mousedown.stop="startResize('e')"></div>
      <!-- 上边缘 -->
      <div class="resize-edge resize-n" @mousedown.stop="startResize('n')"></div>
      <!-- 下边缘 -->
      <div class="resize-edge resize-s" @mousedown.stop="startResize('s')"></div>
      <!-- 左上角 -->
      <div class="resize-corner resize-nw" @mousedown.stop="startResize('nw')"></div>
      <!-- 右上角 -->
      <div class="resize-corner resize-ne" @mousedown.stop="startResize('ne')"></div>
      <!-- 左下角 -->
      <div class="resize-corner resize-sw" @mousedown.stop="startResize('sw')"></div>
      <!-- 右下角 -->
      <div class="resize-corner resize-se" @mousedown.stop="startResize('se')"></div>
    </template>

    <div :class="['relative bg-[#0f0f0f] flex video-container', isMinimized ? 'h-full' : 'w-full h-full']">
      <!-- 视频播放区域 -->
      <div :class="[
        'video-section',
        isMinimized ? 'w-full' : resizeState.width
      ]">
        <div class="flex-grow relative">
          <VideoPlayer
            v-if="video"
            :key="video.id"
            :video="video"
            :initialTime="startTime"
            @play="onVideoPlay"
            @pause="onVideoPause"
            @ended="onVideoEnded"
            @timeupdate="onVideoTimeUpdate"
            class="w-full h-full"
            ref="playerRef"
          />
          
          <!-- 控制层 - 只在最小化时显示 -->
          <div v-if="isMinimized" 
               class="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-200">
            <!-- 渐变背景 -->
            <div class="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/60"></div>
            
            <!-- 顶部控制栏 -->
            <div class="absolute top-0 left-0 right-0 p-2 flex items-start justify-between">
              <div class="text-white text-sm font-medium line-clamp-2 pr-12">
                {{ video?.title }}
              </div>
              <div class="flex items-center gap-1 flex-shrink-0">
                <button 
                  @click="goToOriginalVideo"
                  class="mini-control-btn"
                  title="在新标签页中打开原视频"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                    <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                  </svg>
                </button>
                <button 
                  @click="toggleMinimize"
                  class="mini-control-btn"
                  title="还原"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-8-2h2v-4h4v-2h-4V7h-2v4H7v2h4z"/>
                  </svg>
                </button>
                <button 
                  @click="close"
                  class="mini-control-btn"
                  title="关闭"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- 底部控制栏 -->
            <div class="absolute bottom-0 left-0 right-0 p-2">
              <div class="flex items-center justify-between">
                <div class="text-white/80 text-xs">
                  {{ getMainChannelInfo(video).name }}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 视频信息区域 - 在非最小化状态下显示 -->
        <div v-if="!isMinimized" class="p-4 bg-[#0f0f0f] border-t border-[#272727]">
          <div class="flex items-start gap-2">
            <h2 class="text-lg font-semibold text-white">{{ video?.title }}</h2>
            <button 
              @click="goToOriginalVideo"
              class="mt-1.5 text-[#aaaaaa] hover:text-white transition-colors duration-150 flex items-center gap-1 text-xs"
              title="在新标签页中打开原视频"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
              </svg>
            </button>
          </div>
          <div class="mt-1">
            <span class="text-xs text-[#aaaaaa]">{{ formatDate(video?.uploaded_at) }}</span>
          </div>
          
          <!-- 频道和演员信息区域 -->
          <div class="mt-4 flex items-center">
            <!-- 主频道信息 -->
            <div class="flex items-center">
              <img 
                :src="mainChannelInfo.avatar" 
                alt="Channel Avatar" 
                class="w-10 h-10 rounded-full mr-3 object-cover"
                referrerpolicy="no-referrer"
              >
              <div class="flex flex-col">
                <p class="text-sm font-medium text-white hover:text-blue-400 cursor-pointer" @click="goToChannel(mainChannelInfo.id)">
                  {{ mainChannelInfo.name }}
                </p>
                <p class="text-xs text-[#aaaaaa] mt-0.5">主频道</p>
              </div>
            </div>

            <!-- 演员信息 -->
            <div v-if="hasActors" class="flex items-center ml-6 pl-6 border-l border-[#272727] flex-grow overflow-hidden">
              <div class="flex items-center gap-2 overflow-x-auto custom-scrollbar-x">
                <div 
                  v-for="actor in actorChannels" 
                  :key="actor.id"
                  class="flex items-center px-3 py-1.5 rounded-full hover:bg-[#272727] transition-colors duration-150 cursor-pointer group min-w-fit"
                  @click="goToChannel(actor.id)"
                >
                  <img 
                    :src="actor.avatar" 
                    alt="Actor Avatar" 
                    class="w-6 h-6 rounded-full mr-2 object-cover"
                    referrerpolicy="no-referrer"
                  >
                  <span class="text-sm text-[#aaaaaa] group-hover:text-white transition-colors duration-150 whitespace-nowrap">
                    {{ actor.name }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 播放列表 - 在非最小化状态下显示 -->
      <div v-if="!isMinimized" 
           class="playlist-section"
           :style="{ width: `${resizeState.playlistWidth}px` }"
      >
        <div class="text-white text-lg font-semibold p-4 border-b border-[#272727] flex items-center relative">
          <span>播放列表</span>
          <span class="text-sm text-[#aaaaaa] ml-2">{{ currentIndex + 1 }} / {{ playlist.length }}</span>
          
          <!-- 添加最小化和关闭按钮 - 只在非最小化状态显示 -->
          <div class="absolute right-4 flex items-center gap-2">
            <button 
              @click="toggleMinimize"
              class="p-2 text-[#aaaaaa] hover:text-white transition-colors duration-150 focus:outline-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-8-2h2v-4h4v-2h-4V7h-2v4H7v2h4z"/>
              </svg>
            </button>
            <button 
              @click="close" 
              class="p-2 text-[#aaaaaa] hover:text-white transition-colors duration-150 focus:outline-none"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
              </svg>
            </button>
          </div>

          <!-- 调整大小手柄 -->
          <div class="resize-handle absolute left-0 top-0 w-1 h-full cursor-col-resize"
               @mousedown="startPlaylistResize"
          ></div>
        </div>
        <div class="flex-grow overflow-y-auto custom-scrollbar">
          <div 
            v-for="(item, index) in playlist" 
            :key="item.id" 
            class="flex p-2 hover:bg-[#272727] cursor-pointer relative"
            :class="{ 'bg-[#383838]': item.id === video?.id }"
            @click="changeVideo(item)"
          >
            <!-- 缩略图部分 -->
            <div class="w-40 h-[5.625rem] relative mr-3 flex-shrink-0">
              <img :src="item.thumbnail" alt="Video thumbnail" class="w-full h-full object-cover">
              <span class="absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1 rounded">
                {{ formatDuration(item.duration) }}
              </span>
              
              <!-- 添加进度条 -->
              <div 
                v-if="item.last_position > 0" 
                class="absolute bottom-0 left-0 right-0 h-[2px] bg-black/40 backdrop-blur-sm"
              >
                <div 
                  class="h-full bg-red-600/90 transition-all duration-200"
                  :style="{ 
                    width: `${((item.last_position / item.total_duration) * 100).toFixed(1)}%`,
                    borderRadius: '1px'
                  }"
                ></div>
              </div>
            </div>

            <!-- 视频信息部分 -->
            <div class="flex-grow min-w-0 flex flex-col justify-between">
              <!-- 标题 -->
              <p class="text-white text-sm line-clamp-2 mb-auto" :class="{ 'font-semibold': item.id === video?.id }">
                {{ item.title }}
              </p>

              <!-- 频道信息 -->
              <div class="relative group">
                <div class="flex items-center">
                  <img 
                    :src="getMainChannelInfo(item).avatar" 
                    alt="Channel Avatar" 
                    class="w-4 h-4 rounded-full mr-1 object-cover"
                    referrerpolicy="no-referrer"
                  >
                  <span class="text-[#aaaaaa] text-xs truncate hover:text-white transition-colors duration-150">
                    {{ getMainChannelInfo(item).name }}
                  </span>
                </div>

                <!-- 悬浮框 -->
                <div 
                  v-if="hasActorsInItem(item)"
                  class="channel-popup opacity-0 invisible group-hover:opacity-100 group-hover:visible absolute left-0 bottom-full mb-2 bg-[#282828] rounded-lg shadow-lg transition-all duration-200 z-50 w-max max-w-[300px] p-3"
                >
                  <div class="flex items-center mb-2">
                    <img 
                      :src="getMainChannelInfo(item).avatar" 
                      alt="Channel Avatar" 
                      class="w-8 h-8 rounded-full mr-2 object-cover"
                      referrerpolicy="no-referrer"
                    >
                    <div class="flex flex-col">
                      <span class="text-white text-sm font-medium">{{ getMainChannelInfo(item).name }}</span>
                      <span class="text-gray-400 text-xs">主频道</span>
                    </div>
                  </div>
                  <div class="h-[1px] bg-gray-700 my-2"></div>
                  <div class="flex flex-col gap-2">
                    <div 
                      v-for="actor in getActorChannels(item)" 
                      :key="actor.id"
                      class="flex items-center group/actor cursor-pointer hover:bg-gray-700/50 p-1 rounded-lg transition-colors duration-150"
                      @click.stop="goToChannel(actor.id)"
                    >
                      <img 
                        :src="actor.avatar" 
                        alt="Actor Avatar" 
                        class="w-5 h-5 rounded-full mr-1.5 object-cover"
                        referrerpolicy="no-referrer"
                      >
                      <span class="text-gray-300 text-xs group-hover/actor:text-white transition-colors duration-150">
                        {{ actor.name }}
                      </span>
                    </div>
                  </div>
                  <div class="absolute -bottom-2 left-4 w-4 h-4 bg-[#282828] transform rotate-45"></div>
                </div>
              </div>
            </div>

            <!-- 播放中图标 -->
            <div v-if="item.id === video?.id" class="ml-2 text-[#aaaaaa] flex-shrink-0 self-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref, computed, inject, watch, nextTick } from 'vue';
import VideoPlayer from './VideoPlayer.vue';
import { useVideoHistory } from '../composables/useVideoHistory';

const props = defineProps({
  isOpen: Boolean,
  video: Object,
  playlist: {
    type: Array,
    default: () => []
  },
  initialTime: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits([
  'close', 
  'videoPlay', 
  'videoPause', 
  'videoEnded', 
  'changeVideo',
  'goToChannel'
]);
const playerRef = ref(null);

const currentIndex = computed(() => {
  return props.playlist.findIndex(item => item.id === props.video?.id);
});

const startTime = computed(() => {
  if (props.video.last_position) {
    if (props.video.total_duration - props.video.last_position < 10) {
      return 0;
    } else {
      return props.video.last_position;
    }
  } else {
    return 0;
  }
})

const close = () => {
  emit('close');
};

const onVideoPlay = () => {
  emit('videoPlay', props.video);
};

const onVideoPause = () => {
  emit('videoPause', props.video);
};

const onVideoEnded = () => {
  // 异步更新观看历史
  updateWatchHistory(
    props.video.video_id,
    props.video.channel_id,
    props.video.duration, 
    props.video.duration
  ).catch(err => {
    console.error('Failed to update watch history:', err);
  });

  // 立即执行下一个视频的播放
  const nextIndex = currentIndex.value + 1;
  if (nextIndex < props.playlist.length) {
    changeVideo(props.playlist[nextIndex]);
  } else {
    emit('videoEnded', props.video);
  }
};

const changeVideo = (newVideo) => {
  emit('changeVideo', newVideo);
};

const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now - date);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 1) return '1 天前';
  if (diffDays <= 7) return `${diffDays} 天前`;
  if (diffDays <= 30) return `${Math.ceil(diffDays / 7)} 周前`;
  if (diffDays <= 365) return `${Math.ceil(diffDays / 30)} 个月前`;
  return `${Math.ceil(diffDays / 365)} 年前`;
};

const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return `${hours ? hours + ':' : ''}${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const handleKeyDown = (event) => {
  if (event.key === 'Escape') {
    close();
  }
};

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
});

// 添加频道信息处理的计算属性
const mainChannelInfo = computed(() => {
  const ids = props.video?.channel_id?.toString().split(',') || [];
  const names = props.video?.channel_name?.toString().split(',') || [];
  const avatars = props.video?.channel_avatar?.toString().split(',') || [];
  
  return {
    id: ids[0] || '',
    name: names[0] || '',
    avatar: avatars[0] || '',
  };
});

const actorChannels = computed(() => {
  if (!props.video) return [];
  
  const ids = props.video.channel_id?.toString().split(',') || [];
  const names = props.video.channel_name?.toString().split(',') || [];
  const avatars = props.video.channel_avatar?.toString().split(',') || [];
  
  return ids.slice(1).map((id, index) => ({
    id: id.trim(),
    name: names[index + 1]?.trim() || '',
    avatar: avatars[index + 1]?.trim() || '',
  })).filter(actor => actor.id && actor.name);
});

const hasActors = computed(() => actorChannels.value.length > 0);

// 添加跳转到频道的方法
const goToChannel = (channelId) => {
  // 这里需要添加 emit 来处理频道跳转
  emit('goToChannel', channelId);
};

// 添加处理播放列表项频道信息的方法
const getMainChannelInfo = (item) => {
  const ids = item.channel_id?.toString().split(',') || [];
  const names = item.channel_name?.toString().split(',') || [];
  const avatars = item.channel_avatar?.toString().split(',') || [];
  
  return {
    id: ids[0] || '',
    name: names[0] || '',
    avatar: avatars[0] || '',
  };
};

const getActorChannels = (item) => {
  const ids = item.channel_id?.toString().split(',') || [];
  const names = item.channel_name?.toString().split(',') || [];
  const avatars = item.channel_avatar?.toString().split(',') || [];
  
  return ids.slice(1).map((id, index) => ({
    id: id.trim(),
    name: names[index + 1]?.trim() || '',
    avatar: avatars[index + 1]?.trim() || '',
  })).filter(actor => actor.id && actor.name);
};

const hasActorsInItem = (item) => {
  return getActorChannels(item).length > 0;
};

const emitter = inject('emitter');

const minimizePlayer = () => {
  if (playerRef.value) {
    const currentTime = playerRef.value.player?.currentTime || 0;
    emitter.emit('minimizePlayer', { 
      video: props.video,
      currentTime: currentTime
    });
    emit('close');
  }
};

watch(() => props.video, async (newVideo) => {
  if (newVideo && newVideo.currentTime) {
    nextTick(() => {
      if (playerRef.value && playerRef.value.player) {
        playerRef.value.player.currentTime = newVideo.currentTime;
      }
    });
  }
}, { immediate: true });

// 添加最小化状态
const isMinimized = ref(false);

// 添加调整大态
const resizeState = ref({
  isResizing: false,
  startX: 0,
  width: '70%',
  playlistWidth: 384, // 默认播放列表宽度
  minPlaylistWidth: 320, // 最小播放列表宽度
  maxPlaylistWidth: 600 // 最大播放列表宽度
});

// 切换最小化状态
const toggleMinimize = () => {
  // 设置动画所需的 CSS 变量
  const root = document.documentElement;
  if (!isMinimized.value) {
    // 最小化时，确保位置合理
    const windowHeight = window.innerHeight;
    position.value = {
      x: 24,
      y: windowHeight - size.value.height - 24
    };
    root.style.setProperty('--final-x', `${position.value.x}px`);
    root.style.setProperty('--final-y', `${position.value.y}px`);
  } else {
    root.style.setProperty('--initial-x', `${position.value.x}px`);
    root.style.setProperty('--initial-y', `${position.value.y}px`);
  }

  // 添���相应的动画类
  const container = document.querySelector('.video-modal-container');
  if (container) {
    container.classList.add(isMinimized.value ? 'maximizing' : 'minimized');
    container.addEventListener('animationend', () => {
      container.classList.remove('maximizing', 'minimized');
    }, { once: true });
  }

  isMinimized.value = !isMinimized.value;
  if (!isMinimized.value) {
    resizeState.value.playlistWidth = 384;
  }
};

// 处理播放列表宽度调整
const handlePlaylistResize = (e) => {
  if (!resizeState.value.isResizing) return;
  
  const delta = resizeState.value.startX - e.clientX;
  const newWidth = resizeState.value.playlistWidth + delta;
  
  // 限制最小和最大宽度
  if (newWidth >= resizeState.value.minPlaylistWidth && 
      newWidth <= resizeState.value.maxPlaylistWidth) {
    resizeState.value.playlistWidth = newWidth;
    resizeState.value.startX = e.clientX;
  }
};

// 停止播放列表宽度调整
const stopPlaylistResize = () => {
  resizeState.value.isResizing = false;
  document.removeEventListener('mousemove', handlePlaylistResize);
  document.removeEventListener('mouseup', stopPlaylistResize);
};

// 修改调整大小相关的方法
const startResize = (direction) => {
  if (!isMinimized.value) return;
  
  resizeState.value = {
    isResizing: true,
    direction,
    startX: event.clientX,
    startY: event.clientY,
    startWidth: size.value.width,
    startHeight: size.value.height,
    startLeft: position.value.x,
    startTop: position.value.y
  };
  
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
};

const handleResize = (e) => {
  if (!resizeState.value.isResizing) return;
  
  const { direction, startX, startY, startWidth, startHeight, startLeft, startTop } = resizeState.value;
  const aspectRatio = 16 / 9;
  const minWidth = 160;
  const maxWidth = 800;
  const deltaX = e.clientX - startX;
  const deltaY = e.clientY - startY;
  
  let newWidth = startWidth;
  let newHeight = startHeight;
  let newLeft = startLeft;
  let newTop = startTop;

  // 根据不同方向计算新的尺寸和位置
  if (direction.includes('e')) {
    newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + deltaX));
    newHeight = newWidth / aspectRatio;
  }
  if (direction.includes('w')) {
    const proposedWidth = Math.max(minWidth, Math.min(maxWidth, startWidth - deltaX));
    if (proposedWidth !== startWidth) {
      newWidth = proposedWidth;
      newHeight = newWidth / aspectRatio;
      newLeft = startLeft + (startWidth - newWidth);
    }
  }
  if (direction.includes('s')) {
    newHeight = Math.max(minWidth / aspectRatio, Math.min(maxWidth / aspectRatio, startHeight + deltaY));
    newWidth = newHeight * aspectRatio;
  }
  if (direction.includes('n')) {
    const proposedHeight = Math.max(minWidth / aspectRatio, Math.min(maxWidth / aspectRatio, startHeight - deltaY));
    if (proposedHeight !== startHeight) {
      newHeight = proposedHeight;
      newWidth = newHeight * aspectRatio;
      newTop = startTop + (startHeight - newHeight);
    }
  }

  // 确保不超出屏幕边界
  if (newLeft < 0) newLeft = 0;
  if (newTop < 0) newTop = 0;
  if (newLeft + newWidth > window.innerWidth) newLeft = window.innerWidth - newWidth;
  if (newTop + newHeight > window.innerHeight) newTop = window.innerHeight - newHeight;

  // 更新状态
  size.value = { width: newWidth, height: newHeight };
  position.value = { x: newLeft, y: newTop };
};

const stopResize = () => {
  resizeState.value.isResizing = false;
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
};

// 在组件卸载时清理事件监听
onUnmounted(() => {
  document.removeEventListener('mousemove', handlePlaylistResize);
  document.removeEventListener('mouseup', stopPlaylistResize);
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
});

// 添加拖动和大小调整状态
const position = ref({ x: 24, y: window.innerHeight - 135 });
const size = ref({ width: 220, height: 124 }); // 16:9 比例
const isDragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });

// 计算迷你播放器样式
const miniPlayerStyle = computed(() => {
  if (isMinimized.value) {
    return {
      transform: `translate(${position.value.x}px, ${position.value.y}px)`,
      width: `${size.value.width}px`,
      height: `${size.value.height}px`,
      transformOrigin: 'bottom left'
    };
  } else {
    return {
      transform: 'none',
      width: '100%',
      height: '100%',
      transformOrigin: 'bottom left'
    };
  }
});

// 修改 startDrag 方法
const startDrag = (e) => {
  // 如果不是最小化状态，或者点击了控制按钮或调整大小手柄，则不启动拖动
  if (!isMinimized.value || 
      e.target.closest('.control-btn, .resize-edge, .resize-corner, button, .custom-scrollbar')) {
    return;
  }
  
  // 阻止默认行为和冒泡
  e.preventDefault();
  e.stopPropagation();
  
  isDragging.value = true;
  dragOffset.value = {
    x: e.clientX - position.value.x,
    y: e.clientY - position.value.y
  };
  
  // 添加全局事件监听
  document.addEventListener('mousemove', handleDrag, { passive: false });
  document.addEventListener('mouseup', stopDrag);
  
  // 添加选中保护 - 应用到整个文档
  document.documentElement.style.userSelect = 'none';
  document.documentElement.style.cursor = 'grabbing';
  
  // 防止文本选中
  window.getSelection().removeAllRanges();
};

// 修改 handleDrag 方法
const handleDrag = (e) => {
  if (!isDragging.value) return;
  
  // 阻止所有默认行为和冒泡
  e.preventDefault();
  e.stopPropagation();
  
  let newX = e.clientX - dragOffset.value.x;
  let newY = e.clientY - dragOffset.value.y;
  
  // 添加边界吸附
  const snapDistance = 20;
  const maxX = window.innerWidth - size.value.width;
  const maxY = window.innerHeight - size.value.height;
  
  // 左边界吸附
  if (newX < snapDistance) newX = 0;
  // 右边界吸附
  if (maxX - newX < snapDistance) newX = maxX;
  // 上边界吸附
  if (newY < snapDistance) newY = 0;
  // 下边界吸附
  if (maxY - newY < snapDistance) newY = maxY;
  
  // 确保不超出窗口边界
  newX = Math.max(0, Math.min(newX, maxX));
  newY = Math.max(0, Math.min(newY, maxY));
  
  position.value = { x: newX, y: newY };
};

// 修改 stopDrag 方法
const stopDrag = () => {
  isDragging.value = false;
  document.removeEventListener('mousemove', handleDrag);
  document.removeEventListener('mouseup', stopDrag);
  
  // 恢复选中和鼠标样式 - 应用到整个文档
  document.documentElement.style.userSelect = '';
  document.documentElement.style.cursor = '';
  
  // 防止触发点击事件
  setTimeout(() => {
    window.getSelection().removeAllRanges();
  }, 0);
};

const { updateWatchHistory } = useVideoHistory();

// 修改 onVideoTimeUpdate 方法
const onVideoTimeUpdate = (currentTime) => {
  // 每5秒记录一次观看进度,异步执行
  if (Math.floor(currentTime) % 5 === 0) {
    updateWatchHistory(
      props.video.video_id,
      props.video.channel_id,
      currentTime,
      props.video.duration
    ).catch(err => {
      console.error('Failed to update watch history:', err);
    });
  }
};

const goToOriginalVideo = () => {
  if (props.video?.url) {
    window.open(props.video.url, '_blank');
  }
};

// 添加窗口大小改变处理函数
const handleWindowResize = () => {
  if (!isMinimized.value) return;
  
  // 获取当前窗口尺寸
  const windowWidth = window.innerWidth;
  const windowHeight = window.innerHeight;
  
  // 确保迷你播放器不会超出新的窗口边界
  position.value = {
    x: Math.min(position.value.x, windowWidth - size.value.width),
    y: Math.min(position.value.y, windowHeight - size.value.height)
  };
  
  // 如果位置为负值，重置到默认位置
  if (position.value.x < 0 || position.value.y < 0) {
    position.value = {
      x: 24,
      y: windowHeight - size.value.height - 24
    };
  }
};

// 在组件挂载时添加事件监听
onMounted(() => {
  window.addEventListener('resize', handleWindowResize);
});

// 在组件卸载时移除事件监听
onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize);
});

</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #606060 #181818;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 2px; /* 将宽度从 4px 减小到 2px */
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #181818;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #606060;
  border-radius: 1px; /* 将圆角从 2px 减小到 1px */
  border: none; /* 移除边框 */
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #909090;
}

button:focus {
  outline: none;
}

/* 添加新的样式 */
.grid-cols-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 确保悬浮效果平滑 */
.transition-colors {
  transition-property: background-color, color;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

/* 添加水平滚动条样式 */
.custom-scrollbar-x {
  scrollbar-width: thin;
  scrollbar-color: #606060 transparent;
  padding-bottom: 4px; /* 为滚动条预留空间 */
  /* 移除最大宽度限制 */
}

.custom-scrollbar-x::-webkit-scrollbar {
  height: 2px;
}

.custom-scrollbar-x::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar-x::-webkit-scrollbar-thumb {
  background-color: #606060;
  border-radius: 1px;
}

.custom-scrollbar-x::-webkit-scrollbar-thumb:hover {
  background-color: #909090;
}

/* 确保最小宽度适合内容 */
.min-w-fit {
  min-width: fit-content;
}

/* 优化间距和对齐 */
.gap-2 {
  gap: 0.5rem;
}

/* 添加边框过渡效果 */
.border-l {
  transition: border-color 0.2s ease;
}

/* 悬浮效果优化 */
.group:hover .text-\[\#aaaaaa\] {
  color: #ffffff;
}

/* 添加播放列表项悬浮框特定样式 */
.channel-popup {
  transform-origin: top left;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.5);
}

.channel-popup::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -8px;
  height: 8px;
  background: transparent;
}

/* 确保弹窗在其他元素之上 */
.group:hover .channel-popup {
  z-index: 1000;
}

/* 添加一些动画效果 */
.group-hover\:opacity-100 {
  transition-delay: 200ms;
}

.group:not(:hover) .channel-popup {
  transition-delay: 0ms;
}

/* 添加新的样式 */
.flex-col {
  flex-direction: column;
}

.justify-between {
  justify-content: space-between;
}

.mb-auto {
  margin-bottom: auto;
}

.self-center {
  align-self: center;
}

/* 添加新的样式 */
.resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  width: 4px;
  height: 100%;
  cursor: col-resize;
  background-color: transparent;
  transition: background-color 0.2s;
  z-index: 10;
}

.resize-handle:hover,
.resize-handle:active {
  background-color: #00a1d6;
}

/* 添加过渡效果 */
.transition-all {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 最小化时的样式 */
.minimized {
  @apply rounded-lg overflow-hidden shadow-lg;
  width: 220px; /* 默认宽度改为 220px */
  height: 124px; /* 保持 16:9 比例 */
  position: fixed;
  left: 24px;
  bottom: 24px;
  background: #000;
  transform-origin: bottom left !important;
  animation: minimize 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 修改小窗标题文字大小 */
.minimized .text-sm {
  font-size: 0.7rem; /* 11px */
}

/* 修改小窗控制按钮大小 */
.minimized .mini-control-btn {
  @apply p-0.5;
}

.minimized .mini-control-btn svg {
  width: 0.875rem; /* 14px */
  height: 0.875rem;
}

/* 修改小窗频道名称大小 */
.minimized .text-xs {
  font-size: 0.625rem; /* 10px */
}

/* 确保视频播放器在最小化时保持比例 */
.minimized .video-player {
  aspect-ratio: 16/9;
}

/* 修复滚动条样式 */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #606060 #181818;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 2px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #181818;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #606060;
  border-radius: 1px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #909090;
}

/* 确保内容不会溢出容器 */
.overflow-hidden {
  overflow: hidden;
}

/* 添加阴影效果 */
.minimized {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* 拖动时禁用过渡效果 */
.dragging {
  transition: none !important;
  cursor: grabbing !important;
  user-select: none !important;
}

.resizing {
  transition: none !important;
  cursor: nw-resize !important;
  user-select: none !important;
}

/* 添加鼠标样式 */
.minimized:not(.dragging):not(.resizing) {
  cursor: grab;
}

/* 防止文字选中 */
.select-none {
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

/* 优化过渡效果 */
.transition-all {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 确保播放列表内容可以选中 */
.custom-scrollbar {
  user-select: text;
  cursor: auto;
}

/* 优化控制钮的点击区域 */
.mini-control-btn {
  cursor: pointer;
  z-index: 10;
}

/* 调整大小手柄样 */
.minimized .resize-handle {
  @apply opacity-0 hover:opacity-100;
  width: 16px;
  height: 16px;
  right: 0;
  bottom: 0;
  cursor: nw-resize;
  background: transparent;
}

/* 添加调整大小时的视觉反馈 */
.minimized .resize-handle::before {
  content: '';
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 6px;
  height: 6px;
  border-right: 2px solid rgba(255, 255, 255, 0.5);
  border-bottom: 2px solid rgba(255, 255, 255, 0.5);
}

/* 优化拖动和调整大小时的视觉效果 */
.minimized:not(.dragging):not(.resizing):hover {
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.minimized.dragging,
.minimized.resizing {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2);
}

/* 控制层样式优化 */
.minimized .control-layer {
  background: linear-gradient(to bottom,
    rgba(0, 0, 0, 0.7) 0%,
    transparent 40%,
    transparent 60%,
    rgba(0, 0, 0, 0.7) 100%
  );
}

/* 添加调整大小的边缘样式 */
.resize-edge {
  position: absolute;
  background: transparent;
  z-index: 10;
}

.resize-w, .resize-e {
  width: 4px;
  height: 100%;
  top: 0;
  cursor: ew-resize;
}

.resize-n, .resize-s {
  height: 4px;
  width: 100%;
  left: 0;
  cursor: ns-resize;
}

.resize-w { left: 0; }
.resize-e { right: 0; }
.resize-n { top: 0; }
.resize-s { bottom: 0; }

.resize-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  background: transparent;
  z-index: 11;
}

.resize-nw { top: 0; left: 0; cursor: nw-resize; }
.resize-ne { top: 0; right: 0; cursor: ne-resize; }
.resize-sw { bottom: 0; left: 0; cursor: sw-resize; }
.resize-se { bottom: 0; right: 0; cursor: se-resize; }

/* 调整大小时的视觉反馈 */
.resizing .resize-edge,
.resizing .resize-corner {
  background: rgba(255, 255, 255, 0.1);
}

/* 鼠标悬停时显示调整区域 */
.resize-edge:hover,
.resize-corner:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* 添加最小化动画类 */
.maximizing {
  animation: maximize 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 定义最大化动画 */
@keyframes maximize {
  0% {
    transform: translate(var(--initial-x), var(--initial-y)) scale(0.3) rotate(-45deg);
  }
  100% {
    transform: translate(0, 0) scale(1) rotate(0deg);
  }
}

/* 确保动画过程中内容不溢出 */
.minimized,
.maximizing {
  @apply overflow-hidden;
}

/* 修改拖动时禁用动画的样式 */
.dragging,
.resizing {
  transition: none !important;
  animation: none !important;
}

/* 修改过渡效果 */
.transition-all {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 修改最小化动画 */
.minimized {
  transform-origin: bottom left !important;
  animation: minimize 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 修改最大化动画 */
.maximizing {
  animation: maximize 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 定义最小化动画 */
@keyframes minimize {
  0% {
    transform: translate(0, 0) scale(1);
  }
  100% {
    transform: translate(var(--final-x), var(--final-y)) scale(0.3);
  }
}

/* 定义最大化动画 */
@keyframes maximize {
  0% {
    transform: translate(var(--initial-x), var(--initial-y)) scale(0.3);
  }
  100% {
    transform: translate(0, 0) scale(1);
  }
}

/* 控制层淡入淡出效果 */
.opacity-0 {
  transition: opacity 0.2s ease-in-out;
}

.hover\:opacity-100:hover {
  transition: opacity 0.2s ease-in-out;
}

/* 添加竖屏布局相关样式 */
@media (max-aspect-ratio: 16/9) {
  /* 非最小化状态下的竖屏布局 */
  .video-container:not(.minimized) {
    flex-direction: column;
  }

  /* 调整视频区域在竖屏下的样式 */
  .video-section:not(.minimized) {
    width: 100% !important;
    height: auto !important;
  }

  /* 调整播放列表在竖屏下的样式 */
  .playlist-section:not(.minimized) {
    width: 100% !important;
    height: auto !important;
    max-height: 40vh;
  }
}

/* 添加视频容器和播放列表的基础类 */
.video-section {
  @apply flex-grow flex flex-col;
}

.playlist-section {
  @apply h-full bg-[#181818] flex flex-col;
}
</style>

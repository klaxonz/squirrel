<template>
  <div v-if="isOpen" 
       :class="[
         'fixed z-50 bg-black transition-all duration-300 video-modal-container',
         isMinimized ? 'minimized shadow-lg rounded-lg overflow-hidden' : 'fixed inset-0',
         isDragging ? 'dragging' : '',
         isResizing ? 'resizing' : ''
       ]"
       :style="miniPlayerStyle"
       tabindex="0"
       @keydown.esc="close"
  >

    <template v-if="isMinimized">
      <!-- 左边缘 -->
      <div class="resize-edge resize-w" @mousedown.stop.prevent="startResize('w')"></div>
      <!-- 右边缘 -->
      <div class="resize-edge resize-e" @mousedown.stop.prevent="startResize('e')"></div>
      <!-- 上边缘 -->
      <div class="resize-edge resize-n" @mousedown.stop.prevent="startResize('n')"></div>
      <!-- 下边缘 -->
      <div class="resize-edge resize-s" @mousedown.stop.prevent="startResize('s')"></div>
      <!-- 左上角 -->
      <div class="resize-corner resize-nw" @mousedown.stop.prevent="startResize('nw')"></div>
      <!-- 右上角 -->
      <div class="resize-corner resize-ne" @mousedown.stop.prevent="startResize('ne')"></div>
      <!-- 左下角 -->
      <div class="resize-corner resize-sw" @mousedown.stop.prevent="startResize('sw')"></div>
      <!-- 右下角 -->
      <div class="resize-corner resize-se" @mousedown.stop.prevent="startResize('se')"></div>
    </template>

    <div :class="['relative bg-[#0f0f0f] flex video-container', isMinimized ? 'h-full' : 'w-full h-full']"
         @mousedown.stop="startDrag">
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
               class="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-200"
               >
            <!-- 渐变背景 - 不应该接收事件 -->
            <div class="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/60"></div>
            
            <!-- 顶部控制栏 - 只有按钮可以接收事件 -->
            <div class="absolute top-0 left-0 right-0 p-2 flex items-start justify-between">
              <div class="text-white text-sm font-medium line-clamp-2 pr-12">
                {{ video?.title }}
              </div>
              <div class="flex items-center gap-1 flex-shrink-0 pointer-events-auto">
                <button 
                  @click.stop="goToOriginalVideo"
                  class="mini-control-btn"
                  title="在新标签页中打开原视频"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                    <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                  </svg>
                </button>
                <button 
                  @click.stop="toggleMinimize"
                  class="mini-control-btn"
                  title="还原"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-8-2h2v-4h4v-2h-4V7h-2v4H7v2h4z"/>
                  </svg>
                </button>
                <button 
                  @click.stop="close"
                  class="mini-control-btn"
                  title="关闭"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- 底部控制栏 - 不接收事件 -->
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
          <div class="flex flex-col">
            <div class="flex items-start justify-between">
              <h2 class="text-sm sm:text-lg font-semibold text-white flex-grow line-clamp-2 sm:line-clamp-none leading-5 sm:leading-6">
                {{ video?.title }}
              </h2>
              <div class="flex items-start gap-4 ml-4 flex-shrink-0">
                <!-- 喜欢按钮 -->
                <div class="flex flex-col items-center">
                  <button 
                    @click="handleToggleLike"
                    class="flex items-center justify-center w-5 h-5 rounded-full 
                           transition-all duration-150 hover:bg-[#272727]"
                    :class="{
                      'text-red-500': video.is_liked === 1,
                      'text-yellow-500': video.is_liked === 0,
                      'text-[#aaaaaa] hover:text-white': video.is_liked === null
                    }"
                  >
                    <svg v-if="video.is_liked === 1"
                         xmlns="http://www.w3.org/2000/svg" 
                         class="h-4 w-4" 
                         viewBox="0 0 20 20" 
                         fill="currentColor"
                    >
                      <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
                    </svg>
                    <svg v-else-if="video.is_liked === 0"
                         xmlns="http://www.w3.org/2000/svg" 
                         class="h-4 w-4" 
                         viewBox="0 0 20 20" 
                         fill="currentColor"
                    >
                      <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.105-1.79l-.05-.025A4 4 0 0011.055 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
                    </svg>
                    <svg v-else
                         xmlns="http://www.w3.org/2000/svg" 
                         class="h-4 w-4" 
                         viewBox="0 0 24 24" 
                         fill="none" 
                         stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                    </svg>
                  </button>
                </div>

                <!-- 原视频按钮 -->
                <div class="flex flex-col items-center">
                  <button 
                    @click="goToOriginalVideo"
                    class="flex items-center justify-center w-5 h-5 rounded-full
                           text-[#aaaaaa] hover:text-white hover:bg-[#272727] 
                           transition-all duration-150"
                    title="在新标签页中打开原视频"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                      <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                    </svg>
                  </button>
                  <span class="text-xs text-[#aaaaaa] mt-1">{{ formatDate(video?.uploaded_at) }}</span>
                </div>
              </div>
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
      </div>

      <!-- 播放列表 - 在非最化状态下显示 -->
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
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-8-2h2v-4h4v-2h-4V7h-2v4H7v2h4z"/>
              </svg>
            </button>
            <button 
              @click="close" 
              class="p-2 text-[#aaaaaa] hover:text-white transition-colors duration-150 focus:outline-none"
            >
              <svg class="w-4 w-4" fill="currentColor" viewBox="0 0 24 24">
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
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
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
import { defineProps, defineEmits, onMounted, onUnmounted, ref, computed, inject, watch, nextTick, toRef } from 'vue';
import VideoPlayer from './VideoPlayer.vue';
import { useVideoHistory } from '../composables/useVideoHistory';
import { formatDate, formatDuration } from '../utils/dateFormat';
import useOptionsMenu from "../composables/useOptionsMenu";

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
  'goToChannel',
  'updateVideo'
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

const  handleKeyDown = (event) => {
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
  playlistWidth: 384, // 默认播放列宽度
  minPlaylistWidth: 320, // 最小播放列表宽度
  maxPlaylistWidth: 600 // 最大播放列表宽度
});

// 切换最小化状态
const toggleMinimize = () => {
  if (!isMinimized.value) {
    // 最小化时，设固定位置
    const windowHeight = window.innerHeight;
    position.value = {
      x: 24,
      y: windowHeight - size.value.height - 24
    };
  }
  
  // 切换状态
  isMinimized.value = !isMinimized.value;
  
  // 重置播放列表宽度（如果是最大化）
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

// 止播放列宽度调整
const stopPlaylistResize = () => {
  resizeState.value.isResizing = false;
  document.removeEventListener('mousemove', handlePlaylistResize);
  document.removeEventListener('mouseup', stopPlaylistResize);
};


// 在组件载时清理事件听
onUnmounted(() => {
  document.removeEventListener('mousemove', handlePlaylistResize);
  document.removeEventListener('mouseup', stopPlaylistResize);
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
});

// 添加拖动大小调整状态
const position = ref({ x: 24, y: window.innerHeight - 180 - 24 });
const size = ref({
  width: 320,  // 16:9 比例的宽度
  height: 180  // 16:9 比例的高度
});

// 修改 miniPlayerStyle computed 属性
const miniPlayerStyle = computed(() => {
  if (!isMinimized.value) {
    return {
      transform: 'none',
      width: '100%',
      height: '100%',
      left: '0',
      top: '0'
    };
  }
  
  return {
    position: 'fixed',
    left: `${position.value.x}px`,
    top: `${position.value.y}px`,
    width: `${size.value.width}px`,
    height: `${size.value.height}px`,
    cursor: isDragging.value ? 'grabbing' : isResizing.value ? 'auto' : 'grab'
  };
});

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

// 简化窗口大小改变处理
const handleWindowResize = () => {
  if (!isMinimized.value) return;
  
  const windowHeight = window.innerHeight;
  position.value = {
    x: 24,
    y: windowHeight - size.value.height - 24
  };
};

// 在组件挂载时添加事件监听
onMounted(() => {
  window.addEventListener('resize', handleWindowResize);
});

// 在组卸载时移除事件监听
onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize);
});

// 在 script setup 中添加新的状态
const isDragging = ref(false);
const dragStartPos = ref({ x: 0, y: 0 });

// 添加拖拽相关的方法
const startDrag = (e) => {
  console.log('startDrag');
  // 如果点击了控制按钮或调整大小的句柄，不处理拖拽
  console.log('e.target', e.target.closest('.xgplayer-controls'));
  if (e.target.closest('button') || 
      e.target.closest('.resize-edge') || 
      e.target.closest('.resize-corner')) {
    console.log('点击了控制按钮或调整大小的句柄');
    return;
  }
  
  isDragging.value = true;
  dragStartPos.value = {
    x: e.clientX - position.value.x,
    y: e.clientY - position.value.y
  };
  console.log('dragStartPos', dragStartPos.value);
  
  document.addEventListener('mousemove', handleDrag);
  document.addEventListener('mouseup', stopDrag);
};

const handleDrag = (e) => {
  console.log('handleDrag');
  if (!isDragging.value) return;
  
  // 计算新位置
  let newX = e.clientX - dragStartPos.value.x;
  let newY = e.clientY - dragStartPos.value.y;
  console.log('newX', newX);
  // 限制不超出窗口边界
  const maxX = window.innerWidth - size.value.width;
  const maxY = window.innerHeight - size.value.height;
  
  newX = Math.max(0, Math.min(maxX, newX));
  newY = Math.max(0, Math.min(maxY, newY));
  
  position.value = { x: newX, y: newY };
  console.log('position', position.value);
};

const stopDrag = () => {
  isDragging.value = false;
  document.removeEventListener('mousemove', handleDrag);
  document.removeEventListener('mouseup', stopDrag);
};

// 添加调整大小的状态
const isResizing = ref(false);
const resizeDirection = ref('');
const resizeStartPos = ref({ x: 0, y: 0 });
const resizeStartSize = ref({ width: 0, height: 0 });
const resizeStartPosition = ref({ x: 0, y: 0 });

// 开始调整大小
const startResize = (direction) => {
  if (!isMinimized.value) return;
  
  isResizing.value = true;
  resizeDirection.value = direction;
  resizeStartPos.value = {
    x: event.clientX,
    y: event.clientY
  };
  resizeStartSize.value = {
    width: size.value.width,
    height: size.value.height
  };
  resizeStartPosition.value = {
    x: position.value.x,
    y: position.value.y
  };
  
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
};

// 处理调整大小
const handleResize = (e) => {
  if (!isResizing.value) return;
  
  const deltaX = e.clientX - resizeStartPos.value.x;
  const deltaY = e.clientY - resizeStartPos.value.y;
  const aspectRatio = 16 / 9;
  const minWidth = 320;
  const maxWidth = window.innerWidth - 48;
  const direction = resizeDirection.value;
  
  let newWidth = resizeStartSize.value.width;
  let newHeight = resizeStartSize.value.height;
  let newX = resizeStartPosition.value.x;
  let newY = resizeStartPosition.value.y;

  // 根据调整方向计算新的尺寸和位置
  if (direction.includes('e')) {
    newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartSize.value.width + deltaX));
    newHeight = newWidth / aspectRatio;
  }
  if (direction.includes('w')) {
    const proposedWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartSize.value.width - deltaX));
    if (proposedWidth !== newWidth) {
      newWidth = proposedWidth;
      newHeight = newWidth / aspectRatio;
      newX = resizeStartPosition.value.x + (resizeStartSize.value.width - newWidth);
    }
  }
  if (direction.includes('s')) {
    newHeight = Math.max(minWidth / aspectRatio, Math.min(maxWidth / aspectRatio, resizeStartSize.value.height + deltaY));
    newWidth = newHeight * aspectRatio;
  }
  if (direction.includes('n')) {
    const proposedHeight = Math.max(minWidth / aspectRatio, Math.min(maxWidth / aspectRatio, resizeStartSize.value.height - deltaY));
    if (proposedHeight !== newHeight) {
      newHeight = proposedHeight;
      newWidth = newHeight * aspectRatio;
      newY = resizeStartPosition.value.y + (resizeStartSize.value.height - newHeight);
    }
  }

  // 确保不超出屏幕边界
  if (newX < 0) newX = 0;
  if (newY < 0) newY = 0;
  if (newX + newWidth > window.innerWidth) newX = window.innerWidth - newWidth;
  if (newY + newHeight > window.innerHeight) newY = window.innerHeight - newHeight;

  // 更新状态
  size.value = { width: newWidth, height: newHeight };
  position.value = { x: newX, y: newY };
};

// 停止调整大小
const stopResize = () => {
  isResizing.value = false;
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
};

const videoRef = toRef(props, 'video');
const { toggleLikeVideo } = useOptionsMenu(videoRef);

const handleToggleLike = async () => {
  await toggleLikeVideo();
  // 通知父组件更新频数据
  emit('updateVideo', {
    ...props.video,
    is_liked: props.video.is_liked
  });
};

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
  padding-bottom: 4px; /* 为滚条留空间 */
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

/* 确保小宽度适合内容 */
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

/* 确保弹窗在他元素之上 */
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

/* 添加新的式 */
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

/* 添加新的式 */
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
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 最小化时的样式 */
.minimized {
  @apply rounded-lg  shadow-lg;
  width: 220px; /* 默认宽度改为 220px */
  height: 124px; /* 保持 16:9 比例 */
  position: fixed;
  left: 24px;
  bottom: 24px;
  background: #000;
  transform-origin: bottom right !important;
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

/* 确保视频播放器在小化时保持比例 */
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

/* 添加最小化动画类 */
.maximizing {
  animation: maximize 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* 定义最大化动画 */
@keyframes maximize {
  0% {
    transform: translate(var(--initial-x), var(--initial-y)) scale(1);
    border-radius: 0.5rem;
  }
  100% {
    transform: translate(0, 0) scale(1);
    border-radius: 0;
  }
}

/* 确保动画过程中内容不溢出 */
.minimized,
.maximizing {
  @apply overflow-hidden;
}

/* 修改过渡效果 */
.transition-all {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 修改最小化动画 */
.minimized {
  transform-origin: bottom left !important;
  animation: minimize 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* 修改最大化动画 */
.maximizing {
  animation: maximize 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* 定义最小化动画 */
@keyframes minimize {
  0% {
    transform: translate(0, 0) scale(1);
    border-radius: 0;
  }
  100% {
    transform: translate(var(--final-x), var(--final-y)) scale(1);
    border-radius: 0.5rem;
  }
}

/* 定义最大化动画 */
@keyframes maximize {
  0% {
    transform: translate(var(--initial-x), var(--initial-y)) scale(1);
    border-radius: 0.5rem;
  }
  100% {
    transform: translate(0, 0) scale(1);
    border-radius: 0;
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

  /* 调整播放列表在竖下的样式 */
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

/* 修改动画相关的类 */
.minimizing {
  animation: minimize 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.maximizing {
  animation: maximize 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.minimized {
  position: fixed !important;
  transform-origin: bottom left;
  width: 320px; /* 使用 JS 中定义的默认宽度 */
  height: 180px;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

@keyframes minimize {
  0% {
    transform: translate(0, 0) scale(1);
    border-radius: 0;
  }
  100% {
    transform: translate(var(--final-x), var(--final-y)) scale(1);
    border-radius: 0.5rem;
  }
}

@keyframes maximize {
  0% {
    transform: translate(var(--initial-x), var(--initial-y)) scale(1);
    border-radius: 0.5rem;
  }
  100% {
    transform: translate(0, 0) scale(1);
    border-radius: 0;
  }
}

/* 修改动画相关样式 */
.video-modal-container {
  will-change: transform;
}

.minimized {
  position: fixed !important;
  transform-origin: bottom left;
}

/* 拖拽时禁用过渡 */
.dragging {
  transition: none !important;
  user-select: none;
}

/* 非拖拽时的过渡效果 */
.transition-all:not(.dragging) {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 鼠标样式 */
.minimized:not(.dragging):not(.resizing) {
  cursor: grab;
}

.minimized.dragging {
  cursor: grabbing !important;
}

/* 添加调整大小的边缘样式 */
.resize-edge {
  position: absolute;
  background: transparent;
  z-index: 20;
  /* 增加际可点击区域 */
  padding: 4px;
  margin: -4px;
}

.resize-edge.resize-e,
.resize-edge.resize-w {
  width: 4px;
  height: 100%;
  top: 0;
  cursor: ew-resize;
}

.resize-edge.resize-n,
.resize-edge.resize-s {
  height: 4px;
  width: 100%;
  left: 0;
  cursor: ns-resize;
}

.resize-edge.resize-e { right: -2px; }
.resize-edge.resize-w { left: -2px; }
.resize-edge.resize-n { top: -2px; }
.resize-edge.resize-s { bottom: -2px; }

/* 添加调整大小的角落样式 */
.resize-corner {
  position: absolute;
  width: 12px;
  height: 12px;
  background: transparent;
  z-index: 30;
  /* 增加实际可点击区域 */
  padding: 4px;
  margin: -4px;
}

.resize-corner.resize-nw { 
  top: -4px; 
  left: -4px; 
  cursor: nw-resize;
}
.resize-corner.resize-ne { 
  top: -4px; 
  right: -4px; 
  cursor: ne-resize;
}
.resize-corner.resize-sw { 
  bottom: -4px; 
  left: -4px; 
  cursor: sw-resize;
}
.resize-corner.resize-se { 
  bottom: -4px; 
  right: -4px; 
  cursor: se-resize;
}

/* 拖拽时禁用过渡效果 */
.dragging {
  transition: none !important;
  user-select: none;
}

/* 整大小时禁用过渡效果 */
.resizing {
  transition: none !important;
  user-select: none;
}

/* 非拖拽和调整大小时的过渡效果 */
.transition-all:not(.dragging):not(.resizing) {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 鼠标样式 */
.minimized:not(.dragging):not(.resizing) {
  cursor: grab;
}

.minimized.dragging {
  cursor: grabbing !important;
}

/* 确保拖拽区域在最上层 */
.minimized {
  position: fixed !important;
  transform-origin: bottom left;
  z-index: 1000;
}

/* 确保调整大小的边缘和角落在视频控制层之上 */
.resize-edge,
.resize-corner {
  z-index: 1001;
}

/* 添加调试样式（可选，助查看拖拽区域） */
.resize-edge:hover,
.resize-corner:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* 添加拖拽句柄样式 */
.drag-handle {
  position: absolute;
  inset: 0;
  z-index: 30;
  cursor: grab;
  padding: 8px;
  pointer-events: auto;
}

/* 确保控制按钮在拖拽句柄之上 */
.mini-control-btn {
  position: relative;
  z-index: 40;
}

/* 确保调整大小的边缘和角落在拖拽句柄之上 */
.resize-edge,
.resize-corner {
  z-index: 50;
}

/* 修改拖拽相关样式 */
.dragging .drag-handle {
  cursor: grabbing !important;
}

.drag-handle {
  cursor: grab;
}

/* 确保视频控制层在拖拽句柄之上 */
.video-container {
  position: relative;
  z-index: 20;
}
</style>

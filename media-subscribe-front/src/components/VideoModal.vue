<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black" @keydown.esc="close" tabindex="0">
    <div class="relative w-full h-full bg-[#0f0f0f] flex">
      <!-- 视频播放区域 -->
      <div class="flex-grow flex flex-col h-full">
        <div class="flex-grow relative">
          <VideoPlayer
            v-if="video"
            :key="video.id"
            :video="video"
            :setVideoRef="setVideoRef"
            @play="onVideoPlay"
            @pause="onVideoPause"
            @ended="onVideoEnded"
            class="w-full h-full"
            ref="playerRef"
          />
        </div>
        <div class="p-4 bg-[#0f0f0f] border-t border-[#272727]">
          <div class="flex items-baseline">
            <h2 class="text-lg font-semibold text-white mr-2">{{ video?.title }}</h2>
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

      <!-- 播放列表 -->
      <div class="w-96 h-full bg-[#181818] flex flex-col">
        <div class="text-white text-lg font-semibold p-4 border-b border-[#272727] flex items-center relative">
          <span>播放列表</span>
          <span class="text-sm text-[#aaaaaa] ml-2">{{ currentIndex + 1 }} / {{ playlist.length }}</span>
          <button 
            @click="close" 
            class="absolute right-4 top-1/2 transform -translate-y-1/2 text-[#aaaaaa] hover:text-white transition-colors duration-150 focus:outline-none"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
        <div class="flex-grow overflow-y-auto custom-scrollbar">
          <div 
            v-for="(item, index) in playlist" 
            :key="item.id" 
            class="flex p-2 hover:bg-[#272727] cursor-pointer"
            :class="{ 'bg-[#383838]': item.id === video?.id }"
            @click="changeVideo(item)"
          >
            <!-- 缩略图部分 -->
            <div class="w-40 h-[5.625rem] relative mr-3 flex-shrink-0">
              <img :src="item.thumbnail" alt="Video thumbnail" class="w-full h-full object-cover">
              <span class="absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1 rounded">
                {{ formatDuration(item.duration) }}
              </span>
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
import { defineProps, defineEmits, onMounted, onUnmounted, ref, computed } from 'vue';
import VideoPlayer from './VideoPlayer.vue';

const props = defineProps({
  isOpen: Boolean,
  video: Object,
  setVideoRef: Function,
  playlist: {
    type: Array,
    default: () => []
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
  emit('videoEnded', props.video);
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
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
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
.group:hover .text-[#aaaaaa] {
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
</style>

<template>
  <div v-if="video" 
       class="mini-player fixed bottom-0 left-0 bg-[#0f0f0f] border-t border-[#272727] transition-all duration-300"
       :class="[isCollapsed ? 'w-20' : 'w-64']">
    <div class="relative w-full">
      <!-- 视频容器 -->
      <div class="aspect-video relative">
        <div :id="`mini-player-${video.id}`" class="w-full h-full"></div>
      </div>

      <!-- 视频信息 -->
      <div class="p-2" v-if="!isCollapsed">
        <h3 class="text-xs font-medium text-white line-clamp-2 hover:text-blue-400 cursor-pointer"
            @click="$emit('expandToModal', video)">
          {{ video.title }}
        </h3>
        <div class="flex items-center mt-1">
          <img :src="channelAvatar" 
               alt="Channel Avatar" 
               class="w-4 h-4 rounded-full mr-1"
               referrerpolicy="no-referrer">
          <span class="text-2xs text-gray-400 truncate">{{ channelName }}</span>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="absolute top-2 right-2 flex gap-2">
        <button @click="$emit('expandToModal', video)" 
                class="p-1 rounded-full bg-black/50 hover:bg-black/70 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor">
            <path d="M3 4a1 1 0 011-1h4a1 1 0 010 2H6.414l2.293 2.293a1 1 0 11-1.414 1.414L5 6.414V8a1 1 0 01-2 0V4z" />
            <path d="M17 4a1 1 0 00-1-1h-4a1 1 0 000 2h1.586l-2.293 2.293a1 1 0 001.414 1.414L15 6.414V8a1 1 0 002 0V4z" />
            <path d="M3 16a1 1 0 001 1h4a1 1 0 000-2H6.414l2.293-2.293a1 1 0 00-1.414-1.414L5 13.586V12a1 1 0 00-2 0v4z" />
            <path d="M17 16a1 1 0 00-1 1h-4a1 1 0 000 2h4a1 1 0 001-1v-4a1 1 0 00-2 0v1.586l-2.293-2.293a1 1 0 00-1.414 1.414L13.586 17H12z" />
          </svg>
        </button>
        <button @click="$emit('close')" 
                class="p-1 rounded-full bg-black/50 hover:bg-black/70 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
    <audio ref="audioPlayer" :src="video.audio_url" preload="auto"></audio>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import Player from 'xgplayer';

const props = defineProps({
  video: Object,
  isCollapsed: Boolean,
  currentTime: Number,
});

const emit = defineEmits(['close', 'expandToModal', 'timeUpdate']);

const player = ref(null);
const audioPlayer = ref(null);

const channelName = computed(() => {
  return props.video?.channel_name?.toString().split(',')[0] || '';
});

const channelAvatar = computed(() => {
  return props.video?.channel_avatar?.toString().split(',')[0] || '';
});

const initPlayer = () => {
  if (!props.video?.video_url) return;
  player.value = new Player({
    id: `mini-player-${props.video.id}`,
    url: props.video.video_url,
    poster: props.video.thumbnail,
    autoplay: true,
    volume: 1,
    width: '100%',
    height: '100%',
    cssFullscreen: false,
    startTime: props.currentTime || 0,
    controls: false,
  });

  player.value.on('play', handlePlay);
  player.value.on('pause', handlePause);
  player.value.on('seeking', handleSeeking);
  player.value.on('seeked', handleSeeked);
  player.value.on('timeupdate', handleTimeUpdate);
  player.value.on('ended', handleEnded);
};

const handlePlay = () => {
  audioPlayer.value.play();
};

const handlePause = () => {
  audioPlayer.value.pause();
};

const handleSeeking = () => {
  audioPlayer.value.pause();
};

const handleSeeked = () => {
  audioPlayer.value.currentTime = player.value.currentTime;
  if (!player.value.paused) {
    audioPlayer.value.play();
  }
};

const handleTimeUpdate = () => {
  emit('timeUpdate', player.value.currentTime);
  if (Math.abs(audioPlayer.value.currentTime - player.value.currentTime) > 0.3) {
    audioPlayer.value.currentTime = player.value.currentTime;
  }
};

const handleEnded = () => {
  audioPlayer.value.pause();
  audioPlayer.value.currentTime = 0;
  emit('close');
};

watch(() => props.video, (newVideo) => {
  if (newVideo) {
    if (player.value) {
      player.value.destroy();
    }
    initPlayer();
  }
}, { deep: true });

onMounted(() => {
  if (props.video) {
    initPlayer();
  }
});

onUnmounted(() => {
  if (player.value) {
    player.value.destroy();
  }
});
</script>

<style scoped>
.mini-player {
  z-index: 40;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.2);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style> 
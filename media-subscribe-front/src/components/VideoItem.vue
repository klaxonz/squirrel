<template>
  <div class="video-item bg-white rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200">
    <div class="video-thumbnail relative cursor-pointer aspect-video" @click="playVideo">
      <img
        v-if="!video.isPlaying"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        alt="Video thumbnail"
        class="w-full h-full object-cover"
      >
      <VideoPlayer
        v-if="video.isPlaying"
        :key="video.id"
        :video="video"
        :setVideoRef="setVideoRef"
        @play="onVideoPlay"
        @pause="onVideoPause"
        @ended="onVideoEnded"
      />
      <div v-if="!video.isPlaying" class="video-duration absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1 py-0.5 rounded">
        {{ formatDuration(video.duration) }}
      </div>
    </div>
    <div class="p-2">
      <h3 class="text-sm font-medium text-gray-900 line-clamp-2 mb-1">{{ video.title }}</h3>
      <div class="flex items-center justify-between text-xs text-gray-500">
        <span class="truncate">{{ video.channel_name }}</span>
        <span>{{ formatDate(video.uploaded_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref } from 'vue';
import VideoPlayer from './VideoPlayer.vue';

const props = defineProps({
  video: Object,
  showAvatar: {
    type: Boolean,
    default: true
  },
  setVideoRef: Function,
});

const emit = defineEmits([
  'play', 'setVideoRef', 'videoPlay', 'videoPause', 'videoEnded',
  'toggleOptions', 'goToChannel',
  'videoEnterViewport', 'videoLeaveViewport'
]);

const playVideo = () => {
  console.log('Attempting to play video:', props.video);
  emit('play', props.video);
};

const onVideoPlay = () => {
  console.log('Video started playing');
  emit('videoPlay', props.video);
};

const onVideoPause = () => {
  console.log('Video paused');
  emit('videoPause', props.video);
};

const onVideoEnded = () => {
  console.log('Video ended');
  emit('videoEnded', props.video);
};

const videoItemRef = ref(null);
const observer = ref(null);

onMounted(() => {
  observer.value = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting && props.video.isPlaying) {
        emit('videoLeaveViewport', props.video);
      }
    },
    { threshold: 0.5 }
  );

  if (videoItemRef.value) {
    observer.value.observe(videoItemRef.value);
  }
});

onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect();
  }
});


const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  const now = new Date();

  // 获取当前日期和目标日期的年、月、日
  const todayYear = now.getFullYear();
  const todayMonth = now.getMonth();
  const todayDay = now.getDate();

  const dateYear = date.getFullYear();
  const dateMonth = date.getMonth();
  const dateDay = date.getDate();

  // 比较日期
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay) {
    return '今天';
  }
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay - 1) {
    return '昨天';
  }

  const diffTime = Math.abs(now - date);
  const diffDays = diffTime / (1000 * 60 * 60 * 24);

  if (diffDays <= 7) return `${Math.floor(diffDays)}天前`;
  if (diffDays <= 30) return `${Math.floor(diffDays / 7)}周前`;
  if (diffDays <= 365) return `${Math.floor(diffDays / 30)}个月前`;
  return `${Math.floor(diffDays / 365)}年前`;
};
</script>

<style scoped>
.video-item {
  @apply transition-shadow duration-200 ease-in-out;
}

.video-item:hover {
  @apply shadow-md;
}

.video-thumbnail {
  @apply relative cursor-pointer;
}

.video-duration {
  @apply absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1 py-0.5 rounded;
}

.aspect-video {
  aspect-ratio: 16 / 9;
}
</style>
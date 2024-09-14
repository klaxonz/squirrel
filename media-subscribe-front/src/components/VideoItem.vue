<template>
  <div class="video-item relative" ref="videoItemRef">
    <div class="video-thumbnail relative cursor-pointer">
      <img
        v-if="!video.isPlaying"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        alt="Video thumbnail"
        class="w-full h-full object-cover"
        @click="playVideo"
      >
      <VideoPlayer
        v-if="video.isPlaying"
        :key="video.id"
        :video="video"
        :setVideoRef="setVideoRef"
        @play="onVideoPlay"
        @pause="onVideoPause"
        @ended="onVideoEnded"
        @fullscreenChange="$emit('fullscreenChange', $event)"
        @metadataLoaded="$emit('videoMetadataLoaded', $event, video)"
      />
      <div v-if="!video.isPlaying" class="video-duration">{{ formatDuration(video.duration) }}</div>
      <div v-if="!video.isPlaying" class="play-button" @click="playVideo">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-12 h-12">
          <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clip-rule="evenodd"/>
        </svg>
      </div>
      <div v-if="video.if_downloaded && !video.isPlaying" class="downloaded-badge absolute top-2 right-2 bg-gray-200 bg-opacity-70 text-gray-700 px-2 py-0.5 rounded-full text-xs font-medium opacity-80 hover:opacity-60 transition-opacity duration-200 backdrop-filter: blur(2px);">
        已下载
      </div>
    </div>
    <div class="video-info p-3 flex flex-col">
      <div class="flex justify-between items-start">
        <a
          :href="video.url"
          target="_blank"
          rel="noopener noreferrer"
          class="video-title text-base font-semibold text-gray-900 hover:text-blue-600 transition-colors duration-200 line-clamp-2 flex-grow pr-2"
        >
          {{ video.title }}
        </a>
        <div class="flex-shrink-0 relative">
          <button @click="$emit('toggleOptions', video.id, $event)"
            class="text-gray-500 hover:text-gray-700 focus:outline-none p-1">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="flex justify-between items-center mt-2">
        <div class="flex items-center cursor-pointer" @click="$emit('goToChannel', video.channel_id)">
          <img
            :src="video.channel_avatar"
            :alt="video.channel_name"
            class="w-6 h-6 rounded-full mr-2"
            referrerpolicy="no-referrer"
          >
          <p class="video-channel text-sm text-gray-600 truncate hover:text-blue-500 transition-colors duration-200">
            {{ video.channel_name }}</p>
        </div>
        <span class="text-xs text-gray-500 whitespace-nowrap">{{ formatDate(video.uploaded_at) }}</span>
      </div>
    </div>
    <div v-if="playbackError" class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div class="text-center">
        <p class="text-white mb-2">{{ playbackError }}</p>
        <button @click="retryPlay(video)" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          重试播放
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, inject, watch, onMounted, onUnmounted, ref } from 'vue';
import VideoPlayer from './VideoPlayer.vue';

const props = defineProps({
  video: Object,
  playbackError: String,
  setVideoRef: Function,
});

const emit = defineEmits([
  'play', 'setVideoRef', 'videoPlay', 'videoPause', 'videoEnded',
  'fullscreenChange', 'videoMetadataLoaded', 'toggleOptions', 'goToChannel',
  'videoEnterViewport', 'videoLeaveViewport' // Add these new events
]);

const { retryPlay } = inject('videoOperations');

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

const onVideoMetadataLoaded = (event) => {
  console.log('Video metadata loaded');
  emit('videoMetadataLoaded', event, props.video);
};

const videoItemRef = ref(null);
const observer = ref(null);
const isInViewport = ref(false);

const checkIfInViewport = (entry) => {
  const viewportHeight = window.innerHeight;
  const verticalOffset = entry.boundingClientRect.top;
  const elementHeight = entry.boundingClientRect.height;

  // Consider the video in viewport if at least 50% of it is visible
  const threshold = elementHeight * 0.5;

  return (
    (verticalOffset > -threshold && verticalOffset < viewportHeight - threshold) ||
    (verticalOffset + elementHeight > threshold && verticalOffset + elementHeight < viewportHeight + threshold)
  );
};

onMounted(() => {
  observer.value = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const verticalOffset = entry.boundingClientRect.top;
      console.log(`Video ${props.video.id} vertical offset: ${verticalOffset.toFixed(2)}px`);

      const inViewport = checkIfInViewport(entry);
      if (inViewport !== isInViewport.value) {
        isInViewport.value = inViewport;
        if (inViewport) {
          emit('videoEnterViewport', props.video);
        } else {
          emit('videoLeaveViewport', props.video);
        }
      }
    });
  }, {
    threshold: [0, 0.25, 0.5, 0.75, 1],
    rootMargin: '0px'
  });

  if (videoItemRef.value) {
    observer.value.observe(videoItemRef.value);
  }
});

onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect();
  }
});

watch(() => props.video.isPlaying, (newValue) => {
  if (newValue) {
    const videoElement = document.querySelector(`#video-${props.video.id}`);
    if (videoElement && videoElement.paused) {
      console.log('Video is playing, attempting to play');
      videoElement.play().catch(error => {
        console.warn('播放失败，可能是由于浏览器策略:', error);
      });
    }
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
  const diffTime = Math.abs(now - date);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 1) return '昨天';
  if (diffDays <= 7) return `${diffDays}天前`;
  if (diffDays <= 30) return `${Math.floor(diffDays / 7)}周前`;
  if (diffDays <= 365) return `${Math.floor(diffDays / 30)}个月前`;
  return `${Math.floor(diffDays / 365)}年前`;
};
</script>

<style scoped>
.video-thumbnail {
  @apply relative pt-[56.25%] cursor-pointer;
  height: 0;
}

.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center bg-black;
}

.video-player {
  @apply w-full h-full object-contain;
}

.video-thumbnail img {
  @apply absolute top-0 left-0 w-full h-full object-cover;
}

.video-duration {
  @apply absolute bottom-2 right-2 bg-black bg-opacity-80 text-white text-xs px-1 py-0.5 rounded;
}

.video-title {
  @apply text-base font-semibold text-gray-900 hover:text-blue-600 transition-colors duration-200 line-clamp-2 flex-grow pr-2;
  text-decoration: none;
}

.video-title:hover {
  text-decoration: none;
}

.video-channel {
  @apply text-sm text-gray-600 truncate hover:text-blue-500 transition-colors duration-200;
}

.play-button {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white opacity-80 cursor-pointer;
}

.video-thumbnail:hover .play-button {
  @apply opacity-100;
}

.downloaded-badge {
  @apply absolute top-2 right-2 bg-gray-200 bg-opacity-70 text-gray-700 px-2 py-0.5 rounded-full text-xs font-medium opacity-80 hover:opacity-60 transition-opacity duration-200;
  backdrop-filter: blur(2px);
}

.video-player::-webkit-media-controls {
  display: flex !important;
  visibility: visible !important;
}

.video-item {
  @apply mb-3 sm:mb-0; /* 在小屏幕上保留下边距，在大屏幕上移除 */
}
</style>
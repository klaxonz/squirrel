<template>
  <div class="video-wrapper">
    <video
      :id="`video-${video.id}`"
      :src="video.video_url"
      :ref="el => setVideoRef(video.id, el)"
      class="video-player"
      controls
      autoplay
      muted
      @play="onVideoPlay"
      @pause="onVideoPause"
      @ended="onVideoEnded"
      @fullscreenchange="$emit('fullscreenChange', $event)"
      @loadedmetadata="onVideoMetadataLoaded"
    ></video>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue';

const props = defineProps({
  video: Object,
  setVideoRef: Function,
});

const emit = defineEmits([
  'play', 'pause', 'ended', 'fullscreenChange', 'metadataLoaded'
]);

const onVideoPlay = () => {
  console.log('Video started playing');
  emit('play', props.video);
};

const onVideoPause = () => {
  console.log('Video paused');
  emit('pause', props.video);
};

const onVideoEnded = () => {
  console.log('Video ended');
  emit('ended', props.video);
};

const onVideoMetadataLoaded = (event) => {
  console.log('Video metadata loaded');
  emit('metadataLoaded', event, props.video);
};

onMounted(() => {
  console.log('VideoPlayer mounted');
});

onUnmounted(() => {
  console.log('VideoPlayer unmounted');
});
</script>

<style scoped>
.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center bg-black;
}

.video-player {
  @apply w-full h-full object-contain;
}

.video-player::-webkit-media-controls {
  display: flex !important;
  visibility: visible !important;
}
</style>
<template>
  <div class="video-wrapper">
    <div :id="`video-player-${video.id}`" class="video-player"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref } from 'vue';
import Player from 'xgplayer';

const props = defineProps({
  video: Object,
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'metadataLoaded']);

const player = ref(null);

onMounted(() => {
  initPlayer();
});

onUnmounted(() => {
  if (player.value) {
    player.value.destroy();
  }
});

watch(() => props.video.video_url, (newUrl) => {
  if (player.value && newUrl) {
    player.value.src = newUrl;
  }
});

const initPlayer = () => {
  player.value = new Player({
    id: `video-player-${props.video.id}`,
    url: props.video.video_url,
    autoplay: true,
    width: '100%',
    volume: 1,
    height: '100%',
    cssFullscreen: false,
    commonStyle: {
      // 播放完成部分进度条底色
      playedColor: '#00a1d6',
      // 进度条底色
      progressColor: 'rgba(255, 255, 255, 0.3)',
    },
  });

  player.value.on('play', () => emit('play', props.video));
  player.value.on('pause', () => emit('pause', props.video));
  player.value.on('ended', () => emit('ended', props.video));
  player.value.on('fullscreenChange', (e) => emit('fullscreenChange', e));
  player.value.on('loadedmetadata', (e) => emit('metadataLoaded', e));
};
</script>

<style scoped>
.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center bg-black;
}

.video-player {
  @apply w-full h-full object-contain;
}
</style>
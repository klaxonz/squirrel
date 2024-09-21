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
  setVideoRef: Function,
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange']);

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
      playedColor: '#00a1d6',
      progressColor: 'rgba(255, 255, 255, 0.3)',
    },
  });

  player.value.on('play', () => emit('play', props.video));
  player.value.on('pause', () => emit('pause', props.video));
  player.value.on('ended', () => emit('ended', props.video));
  player.value.on('fullscreenChange', (isFullscreen) => {
    emit('fullscreenChange', isFullscreen);
  });

  // 将 player 实例传递给父组件
  if (props.setVideoRef) {
    console.log('Calling setVideoRef for video:', props.video.id);
    props.setVideoRef(props.video.id, player.value);
  } else {
    console.warn('setVideoRef function not provided for video:', props.video.id);
  }
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
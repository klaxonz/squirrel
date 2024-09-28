<template>
  <div class="video-wrapper">
    <div :id="`video-player-${video.id}`" class="video-player"></div>
    <audio ref="audioPlayer" :src="video.audio_url" preload="auto"></audio>
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
const audioPlayer = ref(null);

onMounted(() => {
  initPlayer();
});

onUnmounted(() => {
  if (player.value) {
    player.value.destroy();
  }
});

watch(() => [props.video.video_url, props.video.audio_url], ([newVideoUrl, newAudioUrl]) => {
  if (player.value && newVideoUrl) {
    player.value.src = newVideoUrl;
  }
  if (audioPlayer.value && newAudioUrl) {
    audioPlayer.value.src = newAudioUrl;
  }
});

const initPlayer = () => {
  player.value = new Player({
    id: `video-player-${props.video.id}`,
    url: props.video.video_url,
    autoplay: false,
    volume: 1,
    width: '100%',
    height: '100%',
    cssFullscreen: false,
    commonStyle: {
      playedColor: '#00a1d6',
      progressColor: 'rgba(255, 255, 255, 0.3)',
    },
  });

  player.value.on('play', handlePlay);
  player.value.on('pause', handlePause);
  player.value.on('seeking', handleSeeking);
  player.value.on('seeked', handleSeeked);
  player.value.on('timeupdate', handleTimeUpdate);
  player.value.on('ended', handleEnded);
  player.value.on('fullscreenChange', (isFullscreen) => {
    emit('fullscreenChange', isFullscreen);
  });

  if (props.setVideoRef) {
    props.setVideoRef(props.video.id, player.value);
  }
};

const handlePlay = () => {
  audioPlayer.value.play();
  emit('play', props.video);
};

const handlePause = () => {
  audioPlayer.value.pause();
  emit('pause', props.video);
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
  if (Math.abs(audioPlayer.value.currentTime - player.value.currentTime) > 0.1) {
    audioPlayer.value.currentTime = player.value.currentTime;
  }
};

const handleEnded = () => {
  audioPlayer.value.pause();
  audioPlayer.value.currentTime = 0;
  emit('ended', props.video);
};
</script>

<style scoped>
.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center bg-black;
}

.video-player {
  @apply w-full h-full object-contain;
}

audio {
  display: none; /* 隐藏音频元素 */
}
</style>
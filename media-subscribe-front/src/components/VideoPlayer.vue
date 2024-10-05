<template>
  <div class="video-wrapper">
    <div :id="`video-player-${video.id}`" class="video-player"></div>
    <audio ref="audioPlayer" :src="video.audio_url" preload="auto"></audio>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref } from 'vue';
import Player from 'xgplayer';
import useVideoOperations from '../composables/useVideoOperations';

const props = defineProps({
  video: Object,
  setVideoRef: Function,
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange']);

const player = ref(null);
const audioPlayer = ref(null);

const { saveVideoProgress, getVideoProgress, startProgressSaving } = useVideoOperations();

onMounted(async () => {
  const initialProgress = await getVideoProgress(props.video);
  initPlayer(initialProgress);
});

onUnmounted(() => {
  if (player.value) {
    clearInterval(props.video.progressSavingInterval);
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

const initPlayer = (initialProgress) => {
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
    currentTime: initialProgress,
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

  props.video.progressSavingInterval = startProgressSaving(props.video);
};

const handlePlay = () => {
  audioPlayer.value.play();
  emit('play', props.video);
};

const handlePause = () => {
  audioPlayer.value.pause();
  saveVideoProgress(props.video, player.value.currentTime);
  emit('pause', props.video);
};

const handleSeeking = () => {
  audioPlayer.value.pause();
};

const handleSeeked = () => {
  const syncAndPlay = () => {
    audioPlayer.value.currentTime = player.value.currentTime;
    if (!player.value.paused) {
      audioPlayer.value.play().then(() => {
        player.value.play();
      }).catch(error => {
        console.error('Failed to play audio after seeking:', error);
        player.value.pause();
      });
    }
  };

  if (audioPlayer.value.readyState >= 3) { // HAVE_FUTURE_DATA or HAVE_ENOUGH_DATA
    syncAndPlay();
  } else {
    player.value.pause();
    const waitForAudio = () => {
      if (audioPlayer.value.readyState >= 3) {
        syncAndPlay();
        audioPlayer.value.removeEventListener('canplay', waitForAudio);
      }
    };
    audioPlayer.value.addEventListener('canplay', waitForAudio);
  }
};

const handleTimeUpdate = () => {
  console.log('handleTimeUpdate', audioPlayer.value.currentTime, player.value.currentTime);

  if (Math.abs(audioPlayer.value.currentTime - player.value.currentTime) > 1) {
    audioPlayer.value.currentTime = player.value.currentTime + 1;
  }
};

const handleEnded = () => {
  audioPlayer.value.pause();
  audioPlayer.value.currentTime = 0;  
  saveVideoProgress(props.video, 0);
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

</style>
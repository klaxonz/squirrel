<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div :id="`video-player-${video.id}`" class="video-player"></div>
    <audio ref="audioPlayer" :src="video.audio_url" preload="auto"></audio>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref, defineExpose } from 'vue';
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
  if (props.video?.video_url) {
    const initialProgress = await getVideoProgress(props.video);
    initPlayer(initialProgress);
  }
});

onUnmounted(() => {
  if (player.value) {
    clearInterval(props.video.progressSavingInterval);
    player.value.destroy();
  }
});

watch(() => props.video?.video_url, async (newVideoUrl) => {
  if (newVideoUrl) {
    if (!player.value) {
      const initialProgress = await getVideoProgress(props.video);
      initPlayer(initialProgress);
    } else {
      player.value.src = newVideoUrl;
    }
  }
});

watch(() => props.video?.audio_url, (newAudioUrl) => {
  if (audioPlayer.value && newAudioUrl) {
    audioPlayer.value.src = newAudioUrl;
  }
});

const initPlayer = (initialProgress) => {
  if (!props.video?.video_url) {
    console.warn('Cannot initialize player: video_url is missing');
    return;
  }

  player.value = new Player({
    id: `video-player-${props.video.id}`,
    url: props.video.video_url,
    poster: props.video.thumbnail,
    autoplay: true,
    volume: 1,
    width: '100%',
    height: '100%',
    cssFullscreen: false,
    currentTime: initialProgress,
    playbackRate: [0.5, 0.75, 1, 1.25, 1.5, 2],
    ignores: ['time'],
    controls: {
      mode: 'flex',
    },
    theme: {
      background: '#000000',
      primary: '#00a1d6',
      progress: '#00a1d6',
      playedColor: '#00a1d6',
      progressColor: 'rgba(255, 255, 255, 0.3)',
      volumeColor: '#00a1d6',
      controlsBgColor: 'rgba(0, 0, 0, 0.5)',
      textColor: '#ffffff',
    },
  });

  player.value.on('play', handlePlay);
  player.value.on('pause', handlePause);
  player.value.on('seeking', handleSeeking);
  player.value.on('seeked', handleSeeked);
  player.value.on('timeupdate', handleTimeUpdate);
  player.value.on('ended', handleEnded);
  player.value.on('waiting', handleWaiting);
  player.value.on('playing', handlePlaying);
  player.value.on('volumechange', handleVolumechange);
  player.value.on('fullscreenChange', (isFullscreen) => {
    emit('fullscreenChange', isFullscreen);
  });

  if (props.setVideoRef) {
    props.setVideoRef(props.video.id, player.value);
  }

  // props.video.progressSavingInterval = startProgressSaving(props.video);
};

const handlePlay = () => {
  console.log('handlePlay', player.value.currentTime)
  audioPlayer.value.play();
  emit('play', props.video);
};

const handlePause = () => {
  audioPlayer.value.pause();
  saveVideoProgress(props.video, player.value.currentTime);
  emit('pause', props.video);
  if(document.visibilityState === 'hidden') {
    player.value.play()
    audioPlayer.value.play();
  }
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

const handleWaiting = () => {
  audioPlayer.value.pause();
};

const handlePlaying = () => {
  audioPlayer.value.play();
};

const handleVolumechange = () => {
  audioPlayer.value.volume = player.value.muted ? 0 : player.value.volume;
};

</script>

<style scoped>
.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center;
}

.video-player {
  @apply w-full h-full object-contain;
}

:deep(.xgplayer) {
  background-color: #0f0f0f;
}

:deep(.xgplayer .xgplayer-controls) {
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8) 0%, rgba(0, 0, 0, 0) 100%);
}

:deep(.xgplayer .xgplayer-slider) {
  background-color: rgba(255, 255, 255, 0.2);
}

:deep(.xgplayer .xgplayer-slider .xgplayer-bar) {
  background-color: #ff0000;
}

:deep(.xgplayer .xgplayer-icon) {
  color: #aaaaaa;
}

:deep(.xgplayer .xgplayer-time) {
  color: #aaaaaa;
}

:deep(.xgplayer .xgplayer-play) {
  border-color: transparent transparent transparent #aaaaaa;
}

:deep(.xgplayer .xgplayer-play.xgplayer-pause::before, .xgplayer .xgplayer-play.xgplayer-pause::after) {
  background-color: #aaaaaa;
}

:deep(.xgplayer .xgplayer-slider .xgplayer-progress) {
  background-color: #ff0000;
}

:deep(.xgplayer .xgplayer-slider .xgplayer-progress-btn) {
  background-color: #ff0000;
}

:deep(.xgplayer .xgplayer-volume .xgplayer-volume-bar) {
  background-color: #aaaaaa;
}

:deep(.xgplayer .xgplayer-volume .xgplayer-volume-active) {
  background-color: #ff0000;
}
</style>

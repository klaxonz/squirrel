<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div :id="`video-player`" class="video-player"></div>
    <audio ref="audioPlayer" :src="video.audio_url" preload="auto"></audio>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref, defineExpose } from 'vue';
import Player from 'xgplayer';
import useVideoOperations from "../composables/useVideoOperations.js";
import {HlsPlugin} from "xgplayer-hls";

const props = defineProps({
  video: Object,
  initialTime: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate']);

const player = ref(null);
const audioPlayer = ref(null);
const {
  playVideo,
} = useVideoOperations();

onMounted(async () => {
  if (!props.video?.video_url) {
    await playVideo(props.video);
    if (props.video.audio_url) {
      audioPlayer.value.src = props.video.audio_url;
    }
  }
  initPlayer();
});

onUnmounted(() => {
  if (player.value) {
    player.value.destroy();
  }
});

watch(() => props.video?.video_url, async (newVideoUrl) => {
  if (newVideoUrl) {
    if (!player.value) {
      initPlayer();
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

watch(() => props.initialTime, (newTime) => {
  if (player.value && newTime > 0) {
    player.value.currentTime = newTime;
  }
});

const initPlayer = () => {
  if (!props.video?.video_url) {
    console.warn('Cannot initialize player: video_url is missing');
    return;
  }
  if (props.video.domain === 'javdb.com') {
    player.value = new Player({
      id: `video-player`,
      url: props.video.video_url,
      poster: props.video.thumbnail,
      autoplay: true,
      volume: 1,
      width: '100%',
      height: '100%',
      cssFullscreen: false,
      startTime: props.initialTime || 0,
      playbackRate: [0.5, 0.75, 1, 1.25, 1.5, 2],
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
      plugins: [HlsPlugin]
    });
  } else {
    player.value = new Player({
      id: `video-player`,
      url: props.video.video_url,
      poster: props.video.thumbnail,
      autoplay: true,
      volume: 1,
      width: '100%',
      height: '100%',
      cssFullscreen: false,
      startTime: props.initialTime || 0,
      playbackRate: [0.5, 0.75, 1, 1.25, 1.5, 2],
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
  }


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
};

const handlePlay = () => {
  if (audioPlayer.value && player.value) {
    audioPlayer.value.play();
    emit('play', props.video);
  }
};

const handlePause = () => {
  if (audioPlayer.value && player.value) {
    audioPlayer.value.pause();
    emit('pause', props.video);
    if(document.visibilityState === 'hidden') {
      player.value.play();
      audioPlayer.value.play();
    }
  }
};

const handleSeeking = () => {
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleSeeked = () => {
  if (!player.value) return;
  
  // 如果没有单独的音频轨道，直接播放视频
  if (!props.video?.audio_url || !audioPlayer.value) {
    if (!player.value.paused) {
      player.value.play();
    }
    return;
  }
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
  syncAndPlay();

};

const handleTimeUpdate = () => {
  if (audioPlayer.value && player.value) {
    const threshold = 0.3;
    const timeDiff = Math.abs(audioPlayer.value.currentTime - player.value.currentTime);
    
    if (timeDiff > threshold) {
      audioPlayer.value.currentTime = player.value.currentTime;
    }
    emit('timeupdate', player.value.currentTime);
  }
};

const handleEnded = () => {
  if (audioPlayer.value && player.value) {
    audioPlayer.value.pause();
    audioPlayer.value.currentTime = 0;  
    emit('ended', props.video);
  }
};

const handleWaiting = () => {
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handlePlaying = () => {
  if (audioPlayer.value) {
    audioPlayer.value.play();
  }
};

const handleVolumechange = () => {
  if (audioPlayer.value && player.value) {
    audioPlayer.value.volume = player.value.muted ? 0 : player.value.volume;
  }
};

defineExpose({
  player
});

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

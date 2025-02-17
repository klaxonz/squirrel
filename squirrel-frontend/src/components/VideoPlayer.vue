<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <video 
      ref="videoPlayer"
      class="video-player"
      :poster="video.thumbnail"
      :src="video.video_stream_url"
      controls
      @play="handlePlay"
      @pause="handlePause"
      @seeked="handleSeeked"
      @seeking="handleSeeking"
      @canplay="handleCanplay"
      @waiting="handleWaiting"
      @playing="handlePlaying"
    ></video>
    <audio ref="audioPlayer" :src="video.audio_stream_url" preload="auto"></audio>
  </div>
</template>

<script setup>
import { onMounted, watch, ref, onBeforeUnmount } from 'vue';
import useVideoOperations from "../composables/useVideoOperations";

const props = defineProps({
  video: Object,
  initialTime: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate']);

const videoPlayer = ref(null);
const audioPlayer = ref(null);
const {
  playVideo,
} = useVideoOperations();


onMounted(async () => {
  if (!props.video?.stream_video_url) {
    await playVideo(props.video);
    if (props.video.stream_audio_url) {
      audioPlayer.value.src = props.video.stream_audio_url;
    }
  }
  if (videoPlayer.value) {
    videoPlayer.value.pause();
  }

});

watch(() => props.video?.stream_video_url, async (newVideoUrl) => {
  if (newVideoUrl && videoPlayer.value) {
    videoPlayer.value.src = newVideoUrl;
  }
});

watch(() => props.video?.stream_audio_url, (newAudioUrl) => {
  if (audioPlayer.value && newAudioUrl) {
    audioPlayer.value.src = newAudioUrl;
  }
});


const handlePlay = () => {
  if (audioPlayer.value && videoPlayer.value) {
    // 先同步时间
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    
    // 先播放音频
    audioPlayer.value.play();
    videoPlayer.value.play();
    
    // 验证播放状态
    const verifyPlayState = () => {
      if (audioPlayer.value.paused || videoPlayer.value.paused) {
        console.warn('Play state mismatch, retrying...');
        audioPlayer.value.play();
        videoPlayer.value.play();
        requestAnimationFrame(verifyPlayState);
      }
    };
    verifyPlayState();
  }
};

const handlePause = () => {
  if (audioPlayer.value && videoPlayer.value) {
    // 先暂停音频
    try {
      audioPlayer.value.pause();
    } catch (e) {
      console.error('Error pausing audio:', e);
    }
    
    // 再暂停视频
    try {
      videoPlayer.value.pause();
    } catch (e) {
      console.error('Error pausing video:', e);
    }
    
    // 状态验证
    const verifyPauseState = () => {
      if (!videoPlayer.value.paused || !audioPlayer.value.paused) {
        console.warn('Pause state mismatch, retrying...');
        audioPlayer.value.pause();
        videoPlayer.value.pause();
        requestAnimationFrame(verifyPauseState);
      }
    };
    verifyPauseState();
  }
};

const handleSeeking = () => {
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleSeeked = () => {
  if (!videoPlayer.value) return;
  if (audioPlayer.value) {
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    if (!videoPlayer.value.paused) {
      audioPlayer.value.play();
    }
  }
};

const handleCanplay = () => {
  console.log('handleCanplay');
  if (videoPlayer.value) {
    videoPlayer.value.play();
  }
};

const handleTimeUpdate = () => {
  emit('timeupdate', videoPlayer.value?.currentTime);
  if (audioPlayer.value && videoPlayer.value) {
    const threshold = 0.3;
    const timeDiff = Math.abs(audioPlayer.value.currentTime - videoPlayer.value.currentTime);
    if (timeDiff > threshold) {
      audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    }
  }
};

const handleEnded = () => {
  if (audioPlayer.value && videoPlayer.value) {
    audioPlayer.value.pause();
    audioPlayer.value.currentTime = 0;  
    emit('ended', props.video);
  }
};

const handleWaiting = () => {
  if (audioPlayer.value) {
    audioPlayer.value.pause();
    // 记录当前播放位置
    const bufferStartTime = videoPlayer.value.currentTime;
    
    // 创建缓冲检查器
    const bufferChecker = setInterval(() => {
      if (videoPlayer.value.readyState > 2) { // 当有足够数据恢复播放时
        clearInterval(bufferChecker);
        // 同步音频到最新视频时间
        const currentVideoTime = videoPlayer.value.currentTime;
        const timeDiff = currentVideoTime - bufferStartTime;
        
        // 如果缓冲期间时间差异过大，直接跳转
        if (timeDiff > 2) {
          audioPlayer.value.currentTime = currentVideoTime;
        } else {
          // 否则渐进式同步
          audioPlayer.value.currentTime = bufferStartTime + timeDiff * 0.8;
        }
        
        if (!videoPlayer.value.paused) {
          audioPlayer.value.play().catch(() => {
            videoPlayer.value.pause();
          });
        }
      }
    }, 300);
  }
};

const handlePlaying = () => {
  if (audioPlayer.value) {
    audioPlayer.value.play();
    
    // 创建同步补偿器
    let syncAttempts = 0;
    const syncCorrector = () => {
      if (syncAttempts++ > 5) return;
      
      const videoTime = videoPlayer.value.currentTime;
      const audioTime = audioPlayer.value.currentTime;
      
      // 渐进式同步策略
      if (Math.abs(videoTime - audioTime) > 0.3) {
        audioPlayer.value.currentTime = videoTime;
      } else if (Math.abs(videoTime - audioTime) > 0.1) {
        // 微调播放速率
        const rate = 1 + (videoTime - audioTime) * 0.1;
        audioPlayer.value.playbackRate = Math.min(Math.max(rate, 0.9), 1.1);
      }
      
      requestAnimationFrame(syncCorrector);
    };
    
    syncCorrector();
  }
};

const handleVolumechange = () => {
  if (audioPlayer.value && videoPlayer.value) {
    audioPlayer.value.volume = videoPlayer.value.muted ? 0 : videoPlayer.value.volume;
  }
};


defineExpose({
  videoPlayer
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

<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <video 
      ref="videoPlayer"
      class="video-player"
      :poster="video.thumbnail"
      :src="video.video_stream_url"
      controls
      @play="handleVideoPlay"
      @pause="handleVideoPause"
      @seeking="handleVideoSeeking"
      @canplay="handleVideoCanplay"
      @waiting="handleVideoWaiting"
    ></video>
    <audio
      ref="audioPlayer"
      :src="video.audio_stream_url"
      @seeking="handleAudioSeeking"
      @canplay="handleAudioCanplay"
      />
  </div>
</template>

<script setup>
import { onMounted, watch, ref } from 'vue';
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

let firstCome = true;
let isVideoCanplay = false;
let isAudioCanplay = false;
let isAudioSeeking = false;
let isVideoSeeking = false;

const isCanplay = () => {
  return isVideoCanplay && isAudioCanplay;
};

const isSeeking = () => {
  return isAudioSeeking || isVideoSeeking;
};

const handleVideoPlay = () => {
  firstCome = false;
  console.log('video play', isVideoCanplay, isAudioCanplay);
  if (isCanplay()) {
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    audioPlayer.value.play();
    console.log(videoPlayer.value.currentTime, audioPlayer.value.currentTime);
  } else {
    videoPlayer.value.pause();
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
  }
};

const handleVideoPause = () => {
  console.log('video pause');
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleVideoSeeking = () => {
  console.log('video seeking');
  audioPlayer.value.pause();
  videoPlayer.value.pause();
  isAudioCanplay = false;
  isVideoCanplay = false;
  isVideoSeeking = true;
};

const handleVideoCanplay = () => {
  console.log('video canplay');
  isVideoCanplay = true;
  isVideoSeeking = false;
  if (!firstCome && !isSeeking() && isCanplay()) {
    videoPlayer.value.play();
    audioPlayer.value.play();
  }
};

const handleVideoWaiting = () => {
  console.log('video waiting');
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleAudioSeeking = () => {
  console.log('audio seeking');
  isAudioSeeking = true;
};

const handleAudioCanplay = () => {
  console.log('audio canplay');
  isAudioCanplay = true;
  isAudioSeeking = false;
  console.log('audio canplay', isSeeking(), isCanplay());
  if (!firstCome && !isSeeking() && isCanplay()) {
    videoPlayer.value.play();
    audioPlayer.value.play();
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


</style>

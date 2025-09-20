import { ref, computed } from 'vue';
import { useVideoApi } from './useVideoApi';

export default function useVideoDetail() {
  const video = ref(null);
  const { getVideoDetail, getSubtitles } = useVideoApi();

  const startTime = computed(() => {
    if (video.value?.last_position) {
      const { last_position } = video.value;
      const total = Number(video.value?.duration) || 0;
      if (!total || total <= 0 || !last_position || last_position <= 0) return 0;

      const progress = (last_position / total) * 100;
      const remainingTime = total - last_position;

      let isNearEnd = false;
      if (total < 300) {
        isNearEnd = progress >= 85;
      } else if (total < 1800) {
        isNearEnd = progress >= 90 || remainingTime < 120;
      } else {
        isNearEnd = progress >= 95 || remainingTime < 180;
      }
      return isNearEnd ? 0 : last_position;
    }
    return 0;
  });

  const fetchVideoDetails = async (videoId) => {
    const { success, data } = await getVideoDetail(videoId);
    if (success) video.value = data;
    return video.value;
  };

  const maybeInjectSubtitles = async (videoId) => {
    if (video.value && /bilibili\.com/.test(video.value.url)) {
      const { success, data } = await getSubtitles(videoId, { lang: 'ai-zh', fmt: 'srt' });
      if (success && typeof data === 'string' && data.length > 0) {
        const blob = new Blob([data], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const subtitle = { id: 'bili-ai-zh', language: '简体中文(AI)', url };
        if (!video.value.subtitles) video.value.subtitles = [];
        video.value.subtitles = [subtitle, ...video.value.subtitles];
      }
    }
  };

  return {
    video,
    startTime,
    fetchVideoDetails,
    maybeInjectSubtitles,
  };
}



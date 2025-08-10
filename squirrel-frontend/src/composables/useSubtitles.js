import { watch } from 'vue';
import { parseVTT, parseSRT } from '../utils/subtitles';

export default function useSubtitles({ playerState, videoRef, props }) {
  const loadSubtitle = async (subtitle) => {
    try {
      if (!subtitle?.url || !videoRef?.value) return;

      const response = await fetch(subtitle.url);
      const text = await response.text();

      // 创建或获取字幕轨道
      let track = videoRef.value.textTracks?.[0];
      if (!track) {
        const label = subtitle.label || subtitle.language || 'Subtitles';
        const langCode = subtitle.srclang || 'zh';
        track = videoRef.value.addTextTrack('subtitles', label, langCode);
      }

      // 清空旧的 cues
      if (track?.cues?.length) {
        for (let i = track.cues.length - 1; i >= 0; i--) {
          track.removeCue(track.cues[i]);
        }
      }

      // 自动识别 SRT/VTT
      const isVtt = text.trimStart().startsWith('WEBVTT');
      if (isVtt) {
        parseVTT(text, track);
      } else {
        parseSRT(text, track);
      }
      track.mode = 'showing';
    } catch (error) {
      console.error('Failed to load subtitle:', error);
    }
  };

  const hideSubtitles = () => {
    if (!videoRef?.value?.textTracks) return;
    for (let i = 0; i < videoRef.value.textTracks.length; i++) {
      videoRef.value.textTracks[i].mode = 'hidden';
    }
  };

  const setSubtitle = (subtitle) => {
    playerState.media.currentSubtitle = subtitle;
    playerState.media.subtitlesEnabled = !!subtitle;

    if (subtitle) {
      loadSubtitle(subtitle);
    } else {
      hideSubtitles();
    }
    playerState.ui.showSettingsMenu = false;
  };

  const toggleSubtitles = () => {
    const willEnable = !playerState.media.subtitlesEnabled;
    playerState.media.subtitlesEnabled = willEnable;

    if (willEnable) {
      const current = playerState.media.currentSubtitle || (props.video?.subtitles?.[0] || null);
      if (current) {
        playerState.media.currentSubtitle = current;
        loadSubtitle(current);
      }
    } else {
      hideSubtitles();
    }
  };

  const ensureSubtitlesOnMetadata = () => {
    if (!videoRef?.value) return;
    if (playerState.media.subtitlesEnabled && playerState.media.currentSubtitle) {
      const track = videoRef.value?.textTracks?.[0];
      if (!track || !track.cues || track.cues.length === 0) {
        loadSubtitle(playerState.media.currentSubtitle);
      } else {
        track.mode = 'showing';
      }
    }
  };

  // 当新字幕列表可用且尚未选择时，自动选择第一条
  watch(() => props.video?.subtitles, (newSubs) => {
    if (Array.isArray(newSubs) && newSubs.length > 0 && !playerState.media.currentSubtitle) {
      const first = newSubs[0];
      playerState.media.currentSubtitle = first;
      playerState.media.subtitlesEnabled = true;
      loadSubtitle(first);
    }
  });

  return {
    toggleSubtitles,
    setSubtitle,
    ensureSubtitlesOnMetadata,
  };
}



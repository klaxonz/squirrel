import { watch } from 'vue';
import { parseVTT, parseSRT } from '../utils/subtitles';

// store: Pinia player store
// videoRef: ref to video element
// props: component props with video object
export default function useSubtitles({ store, videoRef, props }) {
  const getTrack = () => videoRef?.value?.textTracks?.[0] || null;

  const applyCuePosition = (track) => {
    try {
      const pos = store.subtitleSettings?.position || 'bottom';
      if (!track?.cues) return;
      for (let i = 0; i < track.cues.length; i++) {
        const cue = track.cues[i];
        try {
          cue.snapToLines = false;
          cue.line = pos === 'top' ? 10 : 90;
          cue.align = 'center';
        } catch (_) {}
      }
    } catch (_) {}
  };

  const ensureVideoCssClass = () => {
    if (!videoRef?.value) return;
    try {
      videoRef.value.classList.add('subtitle-customized');
    } catch (_) {}
  };

  const updateSubtitleCss = () => {
    if (!videoRef?.value) return;
    ensureVideoCssClass();

    const settings = store.subtitleSettings || {};
    const fontMap = { small: '14px', medium: '18px', large: '24px', xlarge: '32px' };
    const color = settings.color === 'yellow' ? '#ffd54a' : '#ffffff';
    const bg = `rgba(0,0,0,${Math.max(0, Math.min(1, settings.bgOpacity ?? 0.4))})`;
    const fontSize = fontMap[settings.fontSize] || fontMap.medium;
    const shadow = settings.shadow !== false ? '0 2px 4px rgba(0,0,0,0.8)' : 'none';

    const styleId = 'subtitle-style';
    const css = `
      video.subtitle-customized::cue {
        color: ${color};
        background-color: ${bg};
        font-size: ${fontSize};
        text-shadow: ${shadow};
        line-height: 1.35;
        font-weight: 500;
        padding: 0.15em 0.4em;
        border-radius: 0.25em;
      }
    `;

    let styleEl = document.getElementById(styleId);
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = styleId;
      document.head.appendChild(styleEl);
    }
    styleEl.textContent = css;
  };

  const loadSubtitle = async (subtitle) => {
    try {
      if (!subtitle?.url || !videoRef?.value) return;

      const response = await fetch(subtitle.url);
      const text = await response.text();

      let track = getTrack();
      if (!track) {
        const label = subtitle.label || subtitle.language || 'Subtitles';
        const langCode = subtitle.srclang || 'zh';
        track = videoRef.value.addTextTrack('subtitles', label, langCode);
      }

      if (track?.cues?.length) {
        for (let i = track.cues.length - 1; i >= 0; i--) {
          track.removeCue(track.cues[i]);
        }
      }

      const isVtt = text.trimStart().startsWith('WEBVTT');
      const opts = { position: store.subtitleSettings?.position || 'bottom' };
      if (isVtt) {
        parseVTT(text, track, opts);
      } else {
        parseSRT(text, track, opts);
      }
      applyCuePosition(track);
      updateSubtitleCss();
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
    store.setCurrentSubtitle(subtitle);
    store.setSubtitlesEnabled(!!subtitle);

    if (subtitle) {
      loadSubtitle(subtitle);
    } else {
      hideSubtitles();
    }
    store.showSettingsMenu = false;
  };

  const nextSubtitle = () => {
    try {
      const list = Array.isArray(props.video?.subtitles) ? props.video.subtitles : [];
      if (!list.length) return;
      const current = store.currentSubtitle;
      let idx = list.findIndex(s => (s?.url && current?.url && s.url === current.url) || (s === current));
      if (idx === -1) idx = 0; else idx = (idx + 1) % list.length;
      const next = list[idx];
      setSubtitle(next);
    } catch (_) {}
  };

  const toggleSubtitles = () => {
    const willEnable = !store.subtitlesEnabled;
    store.setSubtitlesEnabled(willEnable);

    if (willEnable) {
      const current = store.currentSubtitle || (props.video?.subtitles?.[0] || null);
      if (current) {
        store.setCurrentSubtitle(current);
        loadSubtitle(current);
      }
    } else {
      hideSubtitles();
    }
  };

  const ensureSubtitlesOnMetadata = () => {
    if (!videoRef?.value) return;
    if (store.subtitlesEnabled && store.currentSubtitle) {
      const track = getTrack();
      if (!track || !track.cues || track.cues.length === 0) {
        loadSubtitle(store.currentSubtitle);
      } else {
        applyCuePosition(track);
        updateSubtitleCss();
        track.mode = 'showing';
      }
    }
  };

  watch(() => props.video?.subtitles, (newSubs) => {
    if (Array.isArray(newSubs) && newSubs.length > 0 && !store.currentSubtitle) {
      const first = newSubs[0];
      store.setCurrentSubtitle(first);
      store.setSubtitlesEnabled(true);
      loadSubtitle(first);
    }
  });

  watch(() => store.subtitleSettings, () => {
    try {
      const track = getTrack();
      if (track) applyCuePosition(track);
      updateSubtitleCss();
    } catch (_) {}
  }, { deep: true })

  return {
    toggleSubtitles,
    setSubtitle,
    ensureSubtitlesOnMetadata,
    nextSubtitle,
  };
}

export default function usePlaybackReporting(videoRef, sendReport) {
  let lastReportedTime = 0;

  const onVideoPlay = () => {
    if (videoRef.value) videoRef.value.isPlaying = true;
  };

  const onVideoPause = () => {
    if (videoRef.value) videoRef.value.isPlaying = false;
  };

  const onVideoEnded = () => {
    if (videoRef.value) videoRef.value.if_read = true;
  };

  const onVideoTimeUpdate = (currentTime) => {
    if (!videoRef.value) return;
    if (Math.floor(currentTime) - lastReportedTime >= 2) {
      lastReportedTime = Math.floor(currentTime);
      videoRef.value.last_position = currentTime;
      const total = Number(videoRef.value.duration) || 0;
      videoRef.value.progress = total > 0 ? (currentTime / total) * 100 : 0;
      (async () => {
        try { await sendReport(videoRef.value.id, currentTime); } catch (e) {}
      })();
    }
  };

  return {
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    onVideoTimeUpdate,
  };
}



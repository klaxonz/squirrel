import useVideoDetail from './useVideoDetail';
import useRelatedVideos from './useRelatedVideos';
import useVideoOperations from './useVideoOperations';

export default function usePlaybackOrchestrator() {
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles } = useVideoDetail();
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(video);
  const { playVideo } = useVideoOperations();

  const loadAndPlayById = async (videoId) => {
    if (!videoId) return;
    console.log('[usePlaybackOrchestrator] loadAndPlayById start:', videoId);
    await fetchVideoDetails(videoId);
    console.log('[usePlaybackOrchestrator] after fetchVideoDetails:', {
      hasStreamUrl: !!video.value?.stream_video_url,
      hasMpdUrl: !!video.value?.mpd_url
    });
    try { await maybeInjectSubtitles(videoId); } catch (e) {}
    await fetchRelatedVideos();
    console.log('[usePlaybackOrchestrator] calling playVideo...');
    try { await playVideo(video.value) } catch (e) {}
    console.log('[usePlaybackOrchestrator] after playVideo:', {
      hasStreamUrl: !!video.value?.stream_video_url,
      hasMpdUrl: !!video.value?.mpd_url
    });
  };

  return {
    // state
    video,
    startTime,
    relatedVideos,
    loadingRelated,

    // actions
    loadAndPlayById,
  };
}



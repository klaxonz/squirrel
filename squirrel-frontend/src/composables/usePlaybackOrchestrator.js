import useVideoDetail from './useVideoDetail';
import useRelatedVideos from './useRelatedVideos';
import useVideoOperations from './useVideoOperations';

export default function usePlaybackOrchestrator() {
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles } = useVideoDetail();
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(video);
  const { playVideo } = useVideoOperations();

  const loadAndPlayById = async (videoId) => {
    if (!videoId) return;
    await fetchVideoDetails(videoId);
    try { await maybeInjectSubtitles(videoId); } catch (e) {}
    await fetchRelatedVideos();
    try { await playVideo(video.value) } catch (e) {}
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



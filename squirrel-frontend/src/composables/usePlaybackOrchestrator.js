import useVideoDetail from './useVideoDetail';
import useRelatedVideos from './useRelatedVideos';
import useVideoOperations from './useVideoOperations';

export default function usePlaybackOrchestrator(initialVideo = null) {
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles } = useVideoDetail(initialVideo);
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(video);
  const { playVideo } = useVideoOperations();

  const loadAndPlayById = async (videoId, initialVideoData = null) => {
    if (!videoId) return;
    console.log('[usePlaybackOrchestrator] loadAndPlayById start:', videoId);
    
    // 如果提供了初始视频数据，先设置它以便快速渲染
    if (initialVideoData && initialVideoData.id === videoId) {
      video.value = initialVideoData;
    }
    
    // 如果已经有视频数据且 ID 匹配，后台异步加载完整数据；否则等待加载完成
    const hasInitialData = video.value && video.value.id === videoId;
    
    if (!hasInitialData) {
      // 没有初始数据，正常加载
      await fetchVideoDetails(videoId);
    } else {
      // 有初始数据，后台异步加载完整数据
      fetchVideoDetails(videoId).catch(e => console.error('[usePlaybackOrchestrator] fetchVideoDetails error:', e));
    }
    
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



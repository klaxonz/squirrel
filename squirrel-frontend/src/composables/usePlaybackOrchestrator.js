import { ref } from 'vue';
import useVideoDetail from './useVideoDetail';
import useRelatedVideos from './useRelatedVideos';
import useVideoOperations from './useVideoOperations';
import { Logger } from '@/utils/logger'

export default function usePlaybackOrchestrator(initialVideo = null) {
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles } = useVideoDetail(initialVideo);
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(video);
  const { playVideo } = useVideoOperations();
  const externalError = ref(null);

  const loadAndPlayById = async (videoId, initialVideoData = null, options = {}) => {
    if (!videoId) return;
    Logger.debug('[usePlaybackOrchestrator] loadAndPlayById start', videoId);
    
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
      fetchVideoDetails(videoId).catch(e => Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e));
    }
    
    Logger.debug('[usePlaybackOrchestrator] after fetchVideoDetails', {
      hasStreamUrl: !!video.value?.stream_video_url,
      hasMpdUrl: !!video.value?.mpd_url
    });
    try { await maybeInjectSubtitles(videoId); } catch (e) {}
    await fetchRelatedVideos();

    // 重置外部错误状态
    externalError.value = null;

    Logger.debug('[usePlaybackOrchestrator] calling playVideo (non-blocking)');
    // 仅负责触发播放链接获取，不阻塞 UI 切换到新视频；失败时设置外部错误用于播放器展示
    (async () => {
      try {
        await playVideo(video.value, options);
      } catch (err) {
        const code = err?.code || 'FAILED';
        const message = err?.message || '播放链接获取失败';
        externalError.value = {
          code,
          title: '播放失败',
          message,
          canRetry: true
        };
      }
    })();
    Logger.debug('[usePlaybackOrchestrator] playVideo invoked', {
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
    externalError,

    // actions
    loadAndPlayById,
  };
}



import type { LocaleConfig } from './types'

const enUS: LocaleConfig = {
  code: 'en-US',
  name: 'English',
  messages: {
    // 播放控制
    play: 'Play',
    pause: 'Pause',
    replay: 'Replay',
    stop: 'Stop',
    
    // 音量
    mute: 'Mute',
    unmute: 'Unmute',
    volume: 'Volume',
    
    // 进度
    seek: 'Seek',
    seekTo: 'Seek to',
    currentTime: 'Current time',
    duration: 'Duration',
    remaining: 'Remaining',
    
    // 全屏
    fullscreen: 'Fullscreen',
    exitFullscreen: 'Exit fullscreen',
    
    // 宽屏
    widescreen: 'Theater mode',
    exitWidescreen: 'Exit theater mode',
    
    // 画中画
    pictureInPicture: 'Picture in Picture',
    exitPictureInPicture: 'Exit Picture in Picture',
    
    // 设置
    settings: 'Settings',
    quality: 'Quality',
    codec: 'Codec',
    playbackSpeed: 'Playback speed',
    speedNormal: 'Normal',
    
    // 字幕
    subtitles: 'Subtitles',
    subtitlesOff: 'Off',
    subtitleSettings: 'Subtitle settings',
    fontSize: 'Font size',
    fontColor: 'Font color',
    backgroundColor: 'Background',
    position: 'Position',
    positionTop: 'Top',
    positionBottom: 'Bottom',
    preset: 'Preset',
    opacity: 'Opacity',
    custom: 'Custom',
    subtitleTiming: 'Subtitle sync',
    subtitleTimingNormal: 'Normal',
    subtitleTimingAdvance: 'Advance {seconds}s',
    subtitleTimingDelay: 'Delay {seconds}s',
    
    // 播放列表
    previousVideo: 'Previous',
    nextVideo: 'Next',
    prev: 'Previous',
    next: 'Next',
    previous: 'Previous',
    
    // 快进快退
    skipForward: 'Skip forward',
    skipBackward: 'Skip backward',
    skipSeconds: '{seconds}s',
    
    // 循环
    loop: 'Loop',
    loopOff: 'Loop off',
    
    // 自动播放
    autoplay: 'Autoplay',
    autoplayNext: 'Autoplay next',
    
    // 加载状态
    loading: 'Loading...',
    buffering: 'Buffering...',
    
    // 错误
    errorTitle: 'Playback Error',
    errorNetwork: 'Network connection failed',
    errorMedia: 'Media loading failed',
    errorDecode: 'Video decode failed',
    errorNotSupported: 'Format not supported',
    errorUnknown: 'Unknown error',
    retry: 'Retry',
    dismiss: 'Dismiss',
    
    // 提示
    volumePercent: 'Volume {percent}%',
    speedPercent: '{speed}x speed',
    
    // 片段标记
    startClipSegment: 'Start clip segment',
    endClipSegment: 'End clip segment',
    markClip: 'Mark',
    clipSaved: 'Clip saved',
    clipSavedAt: 'Clip at {time}',
    delete: 'Delete',

    // 无障碍
    videoPlayer: 'Video Player',
    progressBar: 'Progress bar',
    volumeSlider: 'Volume slider',
    timeSlider: 'Time slider'
  }
}

export default enUS

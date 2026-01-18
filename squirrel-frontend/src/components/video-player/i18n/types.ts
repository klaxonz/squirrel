/**
 * 国际化类型定义
 */

export type LocaleCode = 'zh-CN' | 'zh-TW' | 'en-US' | 'ja-JP' | 'ko-KR'

export interface LocaleMessages {
  // 播放控制
  play: string
  pause: string
  replay: string
  stop: string
  
  // 音量
  mute: string
  unmute: string
  volume: string
  
  // 进度
  seek: string
  seekTo: string
  currentTime: string
  duration: string
  remaining: string
  
  // 全屏
  fullscreen: string
  exitFullscreen: string
  
  // 宽屏
  widescreen: string
  exitWidescreen: string
  
  // 画中画
  pictureInPicture: string
  exitPictureInPicture: string
  
  // 设置
  settings: string
  quality: string
  qualityAuto: string
  playbackSpeed: string
  speedNormal: string
  
  // 字幕
  subtitles: string
  subtitlesOff: string
  subtitleSettings: string
  fontSize: string
  fontColor: string
  backgroundColor: string
  position: string
  positionTop: string
  positionBottom: string
  
  // 播放列表
  previousVideo: string
  nextVideo: string
  
  // 快进快退
  skipForward: string
  skipBackward: string
  skipSeconds: string
  
  // 循环
  loop: string
  loopOff: string
  
  // 自动播放
  autoplay: string
  autoplayNext: string
  
  // 加载状态
  loading: string
  buffering: string
  
  // 错误
  errorTitle: string
  errorNetwork: string
  errorMedia: string
  errorDecode: string
  errorNotSupported: string
  errorUnknown: string
  retry: string
  dismiss: string
  
  // 提示
  volumePercent: string
  speedPercent: string
  
  // 无障碍
  videoPlayer: string
  progressBar: string
  volumeSlider: string
  timeSlider: string
}

export interface LocaleConfig {
  code: LocaleCode
  name: string
  messages: LocaleMessages
}

import type { LocaleConfig } from './types'

const zhCN: LocaleConfig = {
  code: 'zh-CN',
  name: '简体中文',
  messages: {
    // 播放控制
    play: '播放',
    pause: '暂停',
    replay: '重播',
    stop: '停止',
    
    // 音量
    mute: '静音',
    unmute: '取消静音',
    volume: '音量',
    
    // 进度
    seek: '跳转',
    seekTo: '跳转到',
    currentTime: '当前时间',
    duration: '总时长',
    remaining: '剩余时间',
    
    // 全屏
    fullscreen: '全屏',
    exitFullscreen: '退出全屏',
    
    // 宽屏
    widescreen: '宽屏模式',
    exitWidescreen: '退出宽屏',
    
    // 画中画
    pictureInPicture: '画中画',
    exitPictureInPicture: '退出画中画',
    
    // 设置
    settings: '设置',
    quality: '画质',
    qualityAuto: '自动',
    playbackSpeed: '播放速度',
    speedNormal: '正常',
    
    // 字幕
    subtitles: '字幕',
    subtitlesOff: '关闭字幕',
    subtitleSettings: '字幕设置',
    fontSize: '字体大小',
    fontColor: '字体颜色',
    backgroundColor: '背景颜色',
    position: '位置',
    positionTop: '顶部',
    positionBottom: '底部',
    
    // 播放列表
    previousVideo: '上一个',
    nextVideo: '下一个',
    
    // 快进快退
    skipForward: '快进',
    skipBackward: '快退',
    skipSeconds: '{seconds}秒',
    
    // 循环
    loop: '循环播放',
    loopOff: '关闭循环',
    
    // 自动播放
    autoplay: '自动播放',
    autoplayNext: '自动播放',
    
    // 加载状态
    loading: '加载中...',
    buffering: '缓冲中...',
    
    // 错误
    errorTitle: '播放出错',
    errorNetwork: '网络连接失败',
    errorMedia: '媒体加载失败',
    errorDecode: '视频解码失败',
    errorNotSupported: '不支持的视频格式',
    errorUnknown: '未知错误',
    retry: '重试',
    dismiss: '关闭',
    
    // 提示
    volumePercent: '音量 {percent}%',
    speedPercent: '{speed}x 倍速',
    
    // 无障碍
    videoPlayer: '视频播放器',
    progressBar: '播放进度条',
    volumeSlider: '音量滑块',
    timeSlider: '时间滑块'
  }
}

export default zhCN

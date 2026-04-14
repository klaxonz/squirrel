import type { LocaleConfig } from './types'

const jaJP: LocaleConfig = {
  code: 'ja-JP',
  name: '日本語',
  messages: {
    // 播放控制
    play: '再生',
    pause: '一時停止',
    replay: 'リプレイ',
    stop: '停止',
    
    // 音量
    mute: 'ミュート',
    unmute: 'ミュート解除',
    volume: '音量',
    
    // 进度
    seek: 'シーク',
    seekTo: 'シーク先',
    currentTime: '現在時刻',
    duration: '長さ',
    remaining: '残り時間',
    
    // 全屏
    fullscreen: '全画面',
    exitFullscreen: '全画面終了',
    
    // 宽屏
    widescreen: 'シアターモード',
    exitWidescreen: 'シアターモード終了',
    
    // 画中画
    pictureInPicture: 'ピクチャーインピクチャー',
    exitPictureInPicture: 'ピクチャーインピクチャー終了',
    
    // 设置
    settings: '設定',
    quality: '画質',
    codec: 'コーデック',
    playbackSpeed: '再生速度',
    speedNormal: '標準',
    
    // 字幕
    subtitles: '字幕',
    subtitlesOff: 'オフ',
    subtitleSettings: '字幕設定',
    fontSize: 'フォントサイズ',
    fontColor: 'フォント色',
    backgroundColor: '背景色',
    position: '位置',
    positionTop: '上',
    positionBottom: '下',
    preset: 'プリセット',
    opacity: '不透明度',
    custom: 'カスタム',
    
    // 播放列表
    previousVideo: '前へ',
    nextVideo: '次へ',
    prev: '前へ',
    next: '次へ',
    previous: '前へ',
    
    // 快进快退
    skipForward: '早送り',
    skipBackward: '巻き戻し',
    skipSeconds: '{seconds}秒',
    
    // 循环
    loop: 'ループ',
    loopOff: 'ループオフ',
    
    // 自动播放
    autoplay: '自動再生',
    autoplayNext: '次を自動再生',
    
    // 加载状态
    loading: '読み込み中...',
    buffering: 'バッファリング中...',
    
    // 错误
    errorTitle: '再生エラー',
    errorNetwork: 'ネットワーク接続エラー',
    errorMedia: 'メディア読み込みエラー',
    errorDecode: '動画デコードエラー',
    errorNotSupported: 'サポートされていない形式',
    errorUnknown: '不明なエラー',
    retry: '再試行',
    dismiss: '閉じる',
    
    // 提示
    volumePercent: '音量 {percent}%',
    speedPercent: '{speed}倍速',

    // 片段标记
    startClipSegment: 'クリップ開始',
    endClipSegment: 'クリップ終了',
    markClip: 'マーク',
    clipSaved: '保存完了',
    clipSavedAt: '{time} マーク',
    delete: '削除',

    // 无障碍
    videoPlayer: 'ビデオプレーヤー',
    progressBar: '再生バー',
    volumeSlider: '音量スライダー',
    timeSlider: '時間スライダー'
  }
}

export default jaJP

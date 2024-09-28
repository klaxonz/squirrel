import { Plugin } from 'xgplayer'

export default class DualSourcePlugin extends Plugin {
  static get pluginName() {
    return 'dualSource'
  }

  static get defaultConfig() {
    return {
      videoUrl: '',
      audioUrl: ''
    }
  }

  constructor(args) {
    super(args)
  }

  beforePlayerInit() {
    // 在播放器初始化之前设置双源
    this.player.config.url = [
      { src: this.config.videoUrl, type: 'video' },
      { src: this.config.audioUrl, type: 'audio' }
    ]
  }

  afterCreate() {
    // 添加方法以动态更新源
    this.player.updateDualSource = this.updateDualSource.bind(this)
  }

  updateDualSource(videoUrl, audioUrl) {
    this.config.videoUrl = videoUrl
    this.config.audioUrl = audioUrl
    this.player.src = [
      { src: videoUrl, type: 'video' },
      { src: audioUrl, type: 'audio' }
    ]
  }

  destroy() {
    // 清理工作
    delete this.player.updateDualSource
  }
}
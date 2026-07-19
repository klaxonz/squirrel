export const CONFIG = {
  SUPPORTED_PLATFORMS: {
    BILIBILI: {
      domain: 'bilibili.com',
      patterns: {
        channel: /space\.bilibili\.com\/(\d+)/,
        video: /bilibili\.com\/video\//
      }
    },
    YOUTUBE: {
      domain: 'youtube.com',
      patterns: {
        channel: {
          handle: /\/@([^\/\?]+)/,
          id: /\/channel\/(UC[\w-]+)/,
          custom: /\/c\/([^\/\?]+)/
        },
        video: /youtube\.com\/watch\?v=/
      }
    }
  },

  DEFAULT_BACKEND_HOST: 'http://localhost:8000',

  STATUS_DISPLAY_DURATION: 3000,

  MAX_HISTORY_LENGTH: 5,
  STORAGE_KEYS: {
    BACKEND_HOST: 'backendHost',
    BACKEND_HISTORY: 'backendHistory'
  }
}

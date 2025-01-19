import { CONFIG } from './config.js';

export class UrlParser {
  static isSupportedUrl(url) {
    return Object.values(CONFIG.SUPPORTED_PLATFORMS)
      .some(platform => url.includes(platform.domain));
  }

  static getChannelInfo(url) {
    url = url.split('?')[0];
    
    for (const [platform, config] of Object.entries(CONFIG.SUPPORTED_PLATFORMS)) {
      if (!url.includes(config.domain)) continue;
      
      if (platform === 'YOUTUBE') {
        const handleMatch = url.match(config.patterns.channel.handle);
        if (handleMatch) {
          return { id: handleMatch[1], url, platform: platform.toLowerCase(), isHandle: true };
        }
        
        const channelMatch = url.match(config.patterns.channel.id);
        if (channelMatch) {
          return { id: channelMatch[1], url, platform: platform.toLowerCase() };
        }
        
        const customMatch = url.match(config.patterns.channel.custom);
        if (customMatch) {
          return { id: customMatch[1], url, platform: platform.toLowerCase(), isCustom: true };
        }
      } else {
        const match = url.match(config.patterns.channel);
        if (match) {
          return { 
            id: platform === 'PORNHUB' ? match[2] : match[1], 
            url, 
            platform: platform.toLowerCase() 
          };
        }
      }
    }
    return null;
  }

  static isVideoPage(url) {
    return Object.values(CONFIG.SUPPORTED_PLATFORMS)
      .some(platform => platform.patterns.video.test(url));
  }
}

export class UIHelper {
  static showStatus(message, isError = false) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.style.display = 'block';
    status.className = `status ${isError ? 'error' : 'success'}`;
    
    setTimeout(() => {
      status.style.display = 'none';
    }, CONFIG.STATUS_DISPLAY_DURATION);
  }
}

export class ChromeAPI {
  static async getCurrentTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return tab;
  }

  static async sendMessage(action, data) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action, data }, resolve);
    });
  }

  static getStorageData(keys) {
    return new Promise((resolve) => {
      chrome.storage.sync.get(keys, resolve);
    });
  }

  static setStorageData(data) {
    return new Promise((resolve) => {
      chrome.storage.sync.set(data, resolve);
    });
  }
} 
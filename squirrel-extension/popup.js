import { UrlParser, UIHelper, ChromeAPI } from './utils.js';

class PopupManager {
  constructor() {
    this.currentTab = null;
    this.downloadButton = document.getElementById('downloadButton');
    this.subscribeButton = document.getElementById('subscribeButton');
    this.settingsButton = document.getElementById('settingsButton');
    this.statusElement = document.getElementById('status');
  }

  async initialize() {
    this.currentTab = await ChromeAPI.getCurrentTab();
    this.setupEventListeners();
    await this.initializeButtons();
  }

  setupEventListeners() {
    this.downloadButton.addEventListener('click', () => this.handleDownload());
    this.subscribeButton.addEventListener('click', () => this.handleSubscribe());
    this.settingsButton.addEventListener('click', () => chrome.runtime.openOptionsPage());
  }

  async initializeButtons() {
    if (!UrlParser.isSupportedUrl(this.currentTab.url)) {
      this.downloadButton.style.display = 'none';
      this.subscribeButton.style.display = 'none';
      this.statusElement.textContent = '不支持当前网站';
      this.statusElement.className = 'status warning';
      this.statusElement.style.display = 'block';
      return;
    }

    const channelInfo = UrlParser.getChannelInfo(this.currentTab.url);
    if (channelInfo) {
      this.downloadButton.style.display = 'none';
      
      try {
        const response = await ChromeAPI.sendMessage("checkSubscription", { url: channelInfo.url });
        if (response.success) {
          this.subscribeButton.classList.toggle('subscribed', response.data.isSubscribed);
          this.updateSubscribeButtonContent(response.data.isSubscribed);
        }
      } catch (error) {
        console.error('检查订阅状态失败:', error);
        UIHelper.showStatus('检查订阅状态失败', true);
      }
    } else if (UrlParser.isVideoPage(this.currentTab.url)) {
      this.subscribeButton.style.display = 'none';
    } else {
      this.downloadButton.style.display = 'none';
      this.subscribeButton.style.display = 'none';
      this.statusElement.textContent = '当前页面不是视频或频道页面';
      this.statusElement.className = 'status warning';
      this.statusElement.style.display = 'block';
    }
  }

  updateSubscribeButtonContent(isSubscribed) {
    this.subscribeButton.innerHTML = `
      <svg class="icon" viewBox="0 0 24 24">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <line x1="19" y1="8" x2="19" y2="14"/>
        ${isSubscribed ? '' : '<line x1="22" y1="11" x2="16" y2="11"/>'}
      </svg>
      ${isSubscribed ? '取消订阅' : '订阅频道'}
    `;
  }

  async handleDownload() {
    if (!this.currentTab) return;
    
    const response = await ChromeAPI.sendMessage(
      "download", 
      { url: this.currentTab.url }
    );
    
    if (response.success) {
      UIHelper.showStatus('下载任务已添加');
    } else {
      UIHelper.showStatus('下载失败: ' + response.error, true);
    }
  }

  async handleSubscribe() {
    if (!this.currentTab) return;
    
    const channelInfo = UrlParser.getChannelInfo(this.currentTab.url);
    if (!channelInfo) return;

    const isSubscribed = this.subscribeButton.classList.contains('subscribed');
    const action = isSubscribed ? "unsubscribe" : "subscribe";
    
    try {
      const response = await ChromeAPI.sendMessage(
        action, 
        { url: channelInfo.url }
      );
      
      if (response.success) {
        this.subscribeButton.classList.toggle('subscribed', !isSubscribed);
        this.updateSubscribeButtonContent(!isSubscribed);
        UIHelper.showStatus(isSubscribed ? '已取消订阅' : '订阅成功');
      } else {
        UIHelper.showStatus(isSubscribed ? '取消订阅失败' : '订阅失败', true);
      }
    } catch (error) {
      console.error('订阅操作失败:', error);
      UIHelper.showStatus('操作失败', true);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const popup = new PopupManager();
  popup.initialize();
});
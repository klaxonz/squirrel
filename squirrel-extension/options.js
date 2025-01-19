import { CONFIG } from './config.js';
import { UIHelper, ChromeAPI } from './utils.js';

class OptionsManager {
  constructor() {
    this.backendHostInput = document.getElementById('backendHost');
    this.historyList = document.getElementById('historyList');
    this.saveButton = document.getElementById('saveButton');
    this.clearHistoryButton = document.getElementById('clearHistoryButton');
  }

  async initialize() {
    await this.loadSettings();
    this.setupEventListeners();
  }

  setupEventListeners() {
    this.saveButton.addEventListener('click', () => this.handleSave());
    this.clearHistoryButton.addEventListener('click', () => this.handleClearHistory());
  }

  async loadSettings() {
    const data = await ChromeAPI.getStorageData([
      CONFIG.STORAGE_KEYS.BACKEND_HOST,
      CONFIG.STORAGE_KEYS.BACKEND_HISTORY
    ]);
    
    const currentHost = data[CONFIG.STORAGE_KEYS.BACKEND_HOST] || CONFIG.DEFAULT_BACKEND_HOST;
    this.backendHostInput.value = currentHost;
    
    this.updateHistoryList(
      data[CONFIG.STORAGE_KEYS.BACKEND_HISTORY] || [], 
      currentHost
    );
  }

  updateHistoryList(history, currentHost) {
    this.historyList.innerHTML = history.map(url => `
      <div class="history-item ${url === currentHost ? 'active' : ''}" data-url="${url}">
        <span class="url">${url}</span>
        <div class="actions">
          <button class="history-action" data-action="use" title="使用此地址">
            <svg class="icon" viewBox="0 0 24 24">
              <polyline points="9 11 12 14 22 4"></polyline>
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
          </button>
          <button class="history-action" data-action="remove" title="删除">
            <svg class="icon" viewBox="0 0 24 24">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
    `).join('');

    // 添加事件监听器
    this.historyList.querySelectorAll('.history-item').forEach(item => {
      // 点击整个项目使用该地址
      item.addEventListener('click', (e) => {
        const actionButton = e.target.closest('.history-action');
        if (!actionButton) {
          this.useHistoryItem(item.dataset.url);
        }
      });

      // 处理操作按钮点击
      item.querySelectorAll('.history-action').forEach(button => {
        button.addEventListener('click', (e) => {
          e.stopPropagation(); // 阻止冒泡，避免触发项目的点击事件
          const action = button.dataset.action;
          const url = item.dataset.url;
          
          if (action === 'use') {
            this.useHistoryItem(url);
          } else if (action === 'remove') {
            this.removeHistoryItem(url);
          }
        });
      });
    });
  }

  async useHistoryItem(url) {
    this.backendHostInput.value = url;
    await this.handleSave();
  }

  async removeHistoryItem(urlToRemove) {
    const data = await ChromeAPI.getStorageData([CONFIG.STORAGE_KEYS.BACKEND_HISTORY]);
    let history = data[CONFIG.STORAGE_KEYS.BACKEND_HISTORY] || [];
    
    history = history.filter(url => url !== urlToRemove);
    
    await ChromeAPI.setStorageData({
      [CONFIG.STORAGE_KEYS.BACKEND_HISTORY]: history
    });
    
    this.updateHistoryList(history, this.backendHostInput.value);
    UIHelper.showStatus('已删除历史记录');
  }

  async handleSave() {
    const newBackendHost = this.backendHostInput.value.trim();
    if (!newBackendHost) return;

    try {
      const data = await ChromeAPI.getStorageData([CONFIG.STORAGE_KEYS.BACKEND_HISTORY]);
      let history = data[CONFIG.STORAGE_KEYS.BACKEND_HISTORY] || [];

      if (!history.includes(newBackendHost)) {
        history.unshift(newBackendHost);
        history = history.slice(0, CONFIG.MAX_HISTORY_LENGTH);
      }

      await ChromeAPI.setStorageData({
        [CONFIG.STORAGE_KEYS.BACKEND_HOST]: newBackendHost,
        [CONFIG.STORAGE_KEYS.BACKEND_HISTORY]: history
      });

      this.updateHistoryList(history, newBackendHost);
      UIHelper.showStatus('设置已保存');
    } catch (error) {
      UIHelper.showStatus('保存失败: ' + error.message, true);
    }
  }

  async handleClearHistory() {
    try {
      await ChromeAPI.setStorageData({
        [CONFIG.STORAGE_KEYS.BACKEND_HISTORY]: []
      });
      this.updateHistoryList([], this.backendHostInput.value);
      UIHelper.showStatus('历史记录已清除');
    } catch (error) {
      UIHelper.showStatus('清除失败: ' + error.message, true);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const options = new OptionsManager();
  options.initialize();
}); 
import { CONFIG } from './config.js';
import { UIHelper, ChromeAPI } from './utils.js';

class OptionsManager {
  constructor() {
    this.backendHostInput = document.getElementById('backendHost');
    this.historyList = document.getElementById('historyList');
    this.resetButton = document.getElementById('resetButton');
    this.clearHistoryButton = document.getElementById('clearHistoryButton');
    this.loginButton = document.getElementById('loginButton');
    this.logoutButton = document.getElementById('logoutButton');
    this.emailInput = document.getElementById('email');
    this.passwordInput = document.getElementById('password');
    this.loginForm = document.getElementById('loginForm');
    this.settingsContent = document.getElementById('settingsContent');
  }

  async initialize() {
    await this.loadSettings();
    this.setupEventListeners();
    await this.checkLoginStatus();
  }

  setupEventListeners() {
    this.resetButton.addEventListener('click', () => this.handleReset());
    this.clearHistoryButton.addEventListener('click', () => this.handleClearHistory());
    this.loginButton.addEventListener('click', () => this.handleLogin());
    this.logoutButton.addEventListener('click', () => this.handleLogout());
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
    await this.handleReset();
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

  async handleReset() {
    const newBackendHost = this.backendHostInput.value.trim();
    if (!newBackendHost) return;

    try {
      await ChromeAPI.sendMessage('logout');
      await ChromeAPI.setStorageData({
        [CONFIG.STORAGE_KEYS.BACKEND_HOST]: newBackendHost
      });
      
      await this.checkLoginStatus();
      this.resetButton.style.display = 'none';
    } catch (error) {
      UIHelper.showStatus('Reset failed: ' + error.message, true);
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

  async checkLoginStatus() {
    const data = await ChromeAPI.getStorageData(['token']);
    const isLoggedIn = !!data.token;
    
    this.loginForm.style.display = isLoggedIn ? 'none' : 'block';
    this.settingsContent.style.display = isLoggedIn ? 'block' : 'none';
    this.resetButton.style.display = isLoggedIn ? 'block' : 'none';

  }

  async handleLogin() {
    const email = this.emailInput.value.trim();
    const password = this.passwordInput.value;

    if (!email || !password) {
      UIHelper.showStatus('请输入邮箱和密码', true);
      return;
    }

    const newBackendHost = this.backendHostInput.value.trim();
    if (!newBackendHost) return;

    try {
      await ChromeAPI.setStorageData({
        [CONFIG.STORAGE_KEYS.BACKEND_HOST]: newBackendHost
      });

      const response = await ChromeAPI.sendMessage('login', { 
        email, 
        password 
      });

      if (response.success) {
        UIHelper.showStatus('登录成功');
        await this.checkLoginStatus();
        this.emailInput.value = '';
        this.passwordInput.value = '';
        await this.loadSettings(); // Reload settings after login
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      UIHelper.showStatus('登录失败: ' + error.message, true);
    }
  }

  async handleLogout() {
    try {
      const response = await ChromeAPI.sendMessage('logout');
      if (response.success) {
        UIHelper.showStatus('已退出登录');
        await this.checkLoginStatus();
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      UIHelper.showStatus('退出失败: ' + error.message, true);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const options = new OptionsManager();
  options.initialize();
}); 
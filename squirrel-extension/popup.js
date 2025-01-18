let currentTab = null;

// 显示状态信息
function showStatus(message, isError = false) {
  const status = document.getElementById('status');
  status.textContent = message;
  status.style.display = 'block';
  status.className = `status ${isError ? 'error' : 'success'}`;
  
  setTimeout(() => {
    status.style.display = 'none';
  }, 3000);
}

// 检查URL是否支持
function isSupportedUrl(url) {
  const supportedDomains = [
    'bilibili.com',
    'youtube.com',
    'pornhub.com',
    'javdb.com'
  ];
  
  return supportedDomains.some(domain => url.includes(domain));
}

function getChannelInfo(url) {
  url = url.split('?')[0];
  if (url.includes('bilibili.com')) {
    const match = url.match(/space\.bilibili\.com\/(\d+)/);
    return match ? { id: match[1], url: url, platform: 'bilibili' } : null;
  }
  
  if (url.includes('youtube.com')) {
    // 处理 @handle 格式的频道链接
    const handleMatch = url.match(/\/@([^\/\?]+)/);
    if (handleMatch) {
      return { id: handleMatch[1], url: url, platform: 'youtube', isHandle: true };
    }
    
    // 处理传统的 channel/ID 格式链接
    const channelMatch = url.match(/\/channel\/(UC[\w-]+)/);
    if (channelMatch) {
      return { id: channelMatch[1], url, url, platform: 'youtube' };
    }
    
    // 处理 c/ 格式的自定义链接
    const customMatch = url.match(/\/c\/([^\/\?]+)/);
    if (customMatch) {
      return { id: customMatch[1], url: url, platform: 'youtube', isCustom: true };
    }
    
    return null;
  }
  
  if (url.includes('pornhub.com')) {
    const match = url.match(/\/(users|model|channels|pornstar)\/([^\/\?]+)/i);
    return match ? { id: match[2], url: url, platform: 'pornhub' } : null;
  }
  
  if (url.includes('javdb.com')) {
    const match = url.match(/\/actors\/([^\/\?]+)/);
    return match ? { id: match[1], url: url, platform: 'javdb' } : null;
  }
  
  return null;
}

// 检查是否是视频页面
function isVideoPage(url) {
  if (url.includes('bilibili.com')) {
    // Bilibili 视频页面规则
    return /bilibili\.com\/video\//.test(url);
  }
  
  if (url.includes('youtube.com')) {
    // YouTube 视频页面规则
    return /youtube\.com\/watch\?v=/.test(url);
  }
  
  if (url.includes('pornhub.com')) {
    // Pornhub 视频页面规则
    return /pornhub\.com\/view_video\.php/.test(url);
  }
  
  if (url.includes('javdb.com')) {
    // JavDB 视频页面规则
    return /javdb\.\w+\/v\//.test(url);
  }
  
  return false;
}

// 初始化按钮状态
async function initializeButtons() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tab;
  
  const downloadButton = document.getElementById('downloadButton');
  const subscribeButton = document.getElementById('subscribeButton');
  
  if (!isSupportedUrl(tab.url)) {
    downloadButton.disabled = true;
    subscribeButton.disabled = true;
    showStatus('不支持当前网站', true);
    return;
  }

  // 检查是否是视频页面
  if (!isVideoPage(tab.url)) {
    downloadButton.disabled = true;
  }
  
  // 检查是否在频道页面
  const channelInfo = getChannelInfo(tab.url);
  if (!channelInfo) {
    subscribeButton.disabled = true;
  } else {
    try {
      // 检查订阅状态
      chrome.runtime.sendMessage({
        action: "checkSubscription",
        data: { url: channelInfo.url }
      }, (response) => {
        if (response.success) {
          const isSubscribed = response.data.isSubscribed;
          subscribeButton.innerHTML = `
            <svg class="icon" viewBox="0 0 24 24">
              ${isSubscribed ? `
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <line x1="19" y1="8" x2="19" y2="14"></line>
                <line x1="22" y1="11" x2="16" y2="11"></line>
              ` : `
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <line x1="19" y1="8" x2="19" y2="14"></line>
              `}
            </svg>
            ${isSubscribed ? '取消订阅' : '订阅频道'}
          `;
          subscribeButton.classList.toggle('subscribed', isSubscribed);
        }
      });
    } catch (error) {
      console.error('Error checking subscription:', error);
      subscribeButton.disabled = true;
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const downloadButton = document.getElementById('downloadButton');
  const subscribeButton = document.getElementById('subscribeButton');

  // 下载按钮点击事件
  downloadButton.addEventListener('click', () => {
    if (!currentTab) return;
    
    chrome.runtime.sendMessage({
      action: "download",
      data: { url: currentTab.url }
    }, (response) => {
      if (response.success) {
        showStatus('下载任务已添加');
      } else {
        showStatus('下载失败: ' + response.error, true);
      }
    });
  });

  // 订阅按钮点击事件
  subscribeButton.addEventListener('click', () => {
    if (!currentTab) return;
    
    const channelInfo = getChannelInfo(currentTab.url);
    if (!channelInfo) return;

    const isSubscribed = subscribeButton.textContent === '取消订阅';
    const action = isSubscribed ? "unsubscribe" : "subscribe";
    
    chrome.runtime.sendMessage({
      action: action,
      data: {
        url: channelInfo.url
      }
    }, (response) => {
      if (response.success) {
        subscribeButton.textContent = isSubscribed ? '顶阅频道' : '取消订阅';
        showStatus(isSubscribed ? '已取消订阅' : '订阅成功');
      } else {
        showStatus(isSubscribed ? '取消订阅失败' : '订阅失败', true);
      }
    });
  });

  // 添加设置按钮点击事件
  const settingsButton = document.getElementById('settingsButton');
  settingsButton.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // 初始化按钮状态
  initializeButtons();
});
const SELECTORS = {
  BILIBILI: {
    VIDEO_CARD: '.bili-video-card',
    INFO_BOTTOM: '.bili-video-card__info--bottom',
    VIDEO_TOOLBAR: '.video-toolbar-left-main',
    SUBSCRIBE_BUTTON: '.up-info__btn-panel .follow-btn',
    UP_INFO_CONTAINER: '.up-info-container',
    UP_INFO_DETAIL_CONTAINER: '.h-inner .h-action'
  },
  COMMON: {
    DOWNLOAD_BUTTON: '.ytdlp-btn',
    SUBSCRIBE_BUTTON: '.subscribe-btn',
  }
};

let isHandleVideoPage = false;
let isHandleChannelDetailPage = false;

const DOWNLOAD_ICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
  <polyline points="7 10 12 15 17 10"></polyline>
  <line x1="12" y1="15" x2="12" y2="3"></line>
</svg>
`;

const SUBSCRIBE_ICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
  <circle cx="9" cy="7" r="4"></circle>
  <line x1="19" y1="8" x2="19" y2="14"></line>
  <line x1="22" y1="11" x2="16" y2="11"></line>
</svg>
`;

const createStyledButton = (text, className, clickHandler, icon) => {
  const button = document.createElement('button');
  button.classList.add(className);
  button.addEventListener('click', clickHandler);

  const iconSpan = document.createElement('span');
  iconSpan.innerHTML = icon;
  iconSpan.style.marginRight = '4px';

  button.appendChild(iconSpan);
  button.appendChild(document.createTextNode(text));

  Object.assign(button.style, {
    marginLeft: '10px',
    backgroundColor: '#00a1d6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    padding: '4px 8px',
    fontSize: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  });

  button.addEventListener('mouseover', () => {
    button.style.backgroundColor = '#0091c2';
    button.style.transform = 'translateY(-1px)';
    button.style.boxShadow = '0 2px 4px rgba(0, 161, 214, 0.4)';
  });

  button.addEventListener('mouseout', () => {
    button.style.backgroundColor = '#00a1d6';
    button.style.transform = 'translateY(0)';
    button.style.boxShadow = 'none';
  });

  return button;
};


const createBilibiliSubscribeButton = (text, classNames, clickHandler) => {
  const button = document.createElement('a');
  for (const className of classNames) {
    button.classList.add(className);
  }
  button.addEventListener('click', clickHandler);
  button.appendChild(document.createTextNode(text));
  return button;
};

const download = (url, data) => {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ 
      action: "download", 
      data: { url, ...data } 
    }, (response) => {
      if (response.success) {
        console.log("Download response:", response.data);
        resolve(response.data);
      } else {
        console.error("Error downloading:", response.error);
        reject(response.error);
      }
    });
  });
};

const subscribe = (url, data) => {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ 
      action: "subscribe", 
      data: { url, ...data } 
    }, (response) => {
      if (response.success) {
        console.log("Subscribe response:", response.data);
        resolve(response.data);
      } else {
        console.error("Error subscribing:", response.error);
        reject(response.error);
      }
    });
  });
};

const addDownloadButtonToBilibili = (container) => {
  const videoCards = container.querySelectorAll(SELECTORS.BILIBILI.VIDEO_CARD);
  videoCards.forEach(card => {
    if (!card.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON)) {
      const infoBottom = card.querySelector(SELECTORS.BILIBILI.INFO_BOTTOM);
      if (infoBottom) {
        const videoUrl = card.querySelector('a').href;
        const downloadButton = createStyledButton('', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), () => download(videoUrl, {}), DOWNLOAD_ICON_SVG);
        Object.assign(downloadButton.style, {
          backgroundColor: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '0',
          marginLeft: '10px',
          borderRadius: '50%',
          transition: 'all 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        });
        downloadButton.innerHTML = DOWNLOAD_ICON_SVG;
        downloadButton.addEventListener('mouseover', () => {
          downloadButton.style.backgroundColor = 'rgba(0, 161, 214, 0.1)';
          downloadButton.style.transform = 'scale(1.1)';
        });
        downloadButton.addEventListener('mouseout', () => {
          downloadButton.style.backgroundColor = 'transparent';
          downloadButton.style.transform = 'scale(1)';
        });
        infoBottom.appendChild(downloadButton);
      }
    }
  });
};

const addDownloadButtonToBilibiliVideo = (container) => {
  const toolbar = container.querySelector(SELECTORS.BILIBILI.VIDEO_TOOLBAR);
  if (toolbar && !toolbar.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON)) {
    const videoUrl = window.location.href;
    const downloadButton = createStyledButton('下载', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), () => download(videoUrl, {}), DOWNLOAD_ICON_SVG);
    toolbar.appendChild(downloadButton);
  }
};

const addSubscribeButtonToBilibili = (container) => {
  const toolbar = container.querySelector(SELECTORS.BILIBILI.VIDEO_TOOLBAR);
  const upInfoContainer = container.querySelector(SELECTORS.BILIBILI.UP_INFO_CONTAINER);
  if (!isHandleVideoPage && toolbar && upInfoContainer && !toolbar.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
    isHandleVideoPage = true;
    const channelUrl = getChannelUrlFromBilibili(upInfoContainer);
    if (channelUrl) {
      const channelId = getChannelIdFromUrl(channelUrl);
      checkSubscriptionStatus(channelId).then(isSubscribed => {
        const buttonText = isSubscribed ? '取消订阅' : '订阅';
        const subscribeButton = createStyledButton(buttonText, SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), () => {
          if (isSubscribed) {
            unsubscribe(channelUrl, { channelId });
          } else {
            subscribe(channelUrl, { channelId });
          }
        }, SUBSCRIBE_ICON_SVG);
        toolbar.appendChild(subscribeButton);
        isHandleVideoPage = false;
      })
    }
  }
};

const addSubscribeButtonToBilibiliDetail = (container) => {
  const upInfoContainer = container.querySelector(SELECTORS.BILIBILI.UP_INFO_DETAIL_CONTAINER);
  if (!isHandleChannelDetailPage && upInfoContainer && !upInfoContainer.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
    isHandleChannelDetailPage = true;
    const channelUrl = getChannelUrlFromLocation();
    if (channelUrl) {
      const channelId = getChannelIdFromUrl(channelUrl);
      checkSubscriptionStatus(channelId).then(isSubscribed => {
        const classNames = ['subscribe-btn', 'h-f-btn'];
        const buttonText = isSubscribed ? '取消订阅' : '订阅';
        const subscribeButton = createBilibiliSubscribeButton(buttonText, classNames, () => {
        if (isSubscribed) {
            unsubscribe(channelUrl, { channelId });
          } else {
            subscribe(channelUrl, { channelId });
          }
          subscribeButton.textContent = isSubscribed ? '订阅' : '取消订阅';
        });

        const firstChild = upInfoContainer.firstChild;
        if (firstChild) {
          upInfoContainer.insertBefore(subscribeButton, firstChild);
        } else {
          upInfoContainer.appendChild(subscribeButton);
        }
        isHandleChannelDetailPage = false;
      });
    }
  }
};

const getChannelUrlFromBilibili = (container) => {
  const avatarLink = container.querySelector('.up-avatar');
  if (avatarLink) {
    const href = avatarLink.getAttribute('href');
    if (href.startsWith('//')) {
      return `https:${href}`;
    } else if (href.startsWith('/')) {
      return `https://space.bilibili.com${href}`;
    } else {
      return href;
    }
  }
  return null;
};

const getChannelUrlFromLocation = () => {
  return window.location.href;
};

const getChannelIdFromUrl = (url) => {
  const match = url.match(/space\.bilibili\.com\/(\d+)/);
  return match ? match[1] : null;
};

const observeDOM = (targetNode, config, callback) => {
  const observer = new MutationObserver((mutationsList, observer) => {
    for (let mutation of mutationsList) {
      if (mutation.type === 'childList') {
        callback(targetNode);
      }
    }
  });

  observer.observe(targetNode, config);
};

const addButtonsToPage = (container) => {
  addDownloadButtonToBilibili(container);
  addDownloadButtonToBilibiliVideo(container);
  addSubscribeButtonToBilibili(container);
  addSubscribeButtonToBilibiliDetail(container)
};

const main = () => {
  const config = { childList: true, subtree: true };
  
  // 检查是否在首页（有 #bewly 元素）
  const bewly = document.querySelector('#bewly');
  if (bewly && bewly.shadowRoot) {
    observeDOM(bewly.shadowRoot, config, addButtonsToPage);
  } else {
    // 如果不在首页，直接观察 document.body
    observeDOM(document.body, config, addButtonsToPage);
  }
};

// 等待页面加载完成后开始观察
window.addEventListener('load', () => {
  main();
});

// 由于页面可能在加载后动态变化，我们也在 DOMContentLoaded 后立即运行一次
document.addEventListener('DOMContentLoaded', () => {
  addButtonsToPage(document.body);
});

// 添加这个新函数来检查订阅状态
const checkSubscriptionStatus = (channelId) => {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ 
      action: "checkSubscription", 
      data: { channelId } 
    }, (response) => {
      if (response.success) {
        resolve(response.data.isSubscribed);
      } else {
        console.error("Error checking subscription status:", response.error);
        reject(response.error);
      }
    });
  });
};

// 添加取消订阅的函数
const unsubscribe = (url, data) => {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ 
      action: "unsubscribe", 
      data: { id: data.channelId } 
    }, (response) => {
      if (response.success) {
        console.log("Unsubscribe response:", response.data.data);
        resolve(response.data.data);
      } else {
        console.error("Error unsubscribing:", response.error);
        reject(response.error);
      }
    });
  });
};
const SELECTORS = {
  BILIBILI: {
    VIDEO_CARD: '.bili-video-card',
    INFO_BOTTOM: '.bili-video-card__info--bottom',
    VIDEO_TOOLBAR: '.video-toolbar-left-main',
    SUBSCRIBE_BUTTON: '.up-info__btn-panel .follow-btn',
    UP_INFO_CONTAINER: '.up-info-container',
    UP_INFO_DETAIL_CONTAINER: '.h-inner .h-action'
  },
  YOUTUBE: {
    SUBSCRIBE_CONTAINER: '.page-header-view-model-wiz__page-header-headline-info',
    SUBSCRIBE_BUTTON: '.yt-spec-button-shape-next',
    CHANNEL_NAME: '#channel-name, #owner-name',
    VIDEO_OWNER: '#owner',
    VIDEO_OWNER_LINK: '#owner a',
    CHANNEL_ID_META: 'meta[itemprop="channelId"]',
    CHANNEL_HANDLE: 'yt-formatted-string.ytd-channel-name'
  },
  COMMON: {
    DOWNLOAD_BUTTON: '.ytdlp-btn',
    SUBSCRIBE_BUTTON: '.subscribe-btn',
  },
  PORNHUB: {
    SUBSCRIBE_CONTAINER: '.userButtons, .nameSubscribe',
    CHANNEL_NAME: '#channelsProfile .title > h1, .nameSubscribe .name h1',
    SUBSCRIBE_BUTTON: 'button[data-subscribe-url], .addFriendButton button[data-friend-url]',
    AVATAR: '#getAvatar',
    CHANNEL_LINK: '.usernameBadgesWrapper a',
    VIDEO_UPLOADER: '.video-detailed-info .usernameBadgesWrapper a'
  },
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
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
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
  const url = new URL(window.location.href);
  return `${url.origin}${url.pathname}`;
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

const main = () => {
  const config = { childList: true, subtree: true };
  
  if (window.location.hostname.includes('youtube.com')) {
    let lastUrl = location.href;
    let buttonCheckInterval;

    // 监听 URL 变化
    new MutationObserver(() => {
      const url = location.href;
      if (url !== lastUrl) {
        lastUrl = url;
        console.log('URL changed, re-adding buttons');
        clearInterval(buttonCheckInterval); // 清除旧的检查
        addButtonsToPage(document.body);
        startButtonCheck(); // 开始新的检查
      }
    }).observe(document.body, config);

    // 定义按钮检查函数
    const checkButton = () => {
      const subscribeContainer = document.querySelector(SELECTORS.YOUTUBE.SUBSCRIBE_CONTAINER);
      const existingButton = document.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON);
      
      if (subscribeContainer && !existingButton) {
        console.log('Subscribe container found but button missing, re-adding button');
        addButtonsToPage(document.body);
      }
    };

    // 开始按钮检查的函数
    const startButtonCheck = () => {
      // 60秒后停止检查
      setTimeout(() => {
        checkButton()
      }, 5000);
    };

    // 初始启动按钮检查
    startButtonCheck();
  } else if (window.location.hostname.includes('pornhub.com')) {
    // 对 Pornhub 使用类似的观察逻辑
    let lastUrl = location.href;
    new MutationObserver(() => {
      const url = location.href;
      if (url !== lastUrl) {
        lastUrl = url;
        console.log('URL changed, re-adding buttons');
        setTimeout(() => {
          addButtonsToPage(document.body);
        }, 1000);
      }
    }).observe(document.body, config);
  } else if (window.location.hostname.includes('bilibili.com')) {
    observeDOM(document.body, config, addButtonsToPage);
  }
};

// 保持原有的事件监听，但添加防抖动
let addButtonsTimeout;
window.addEventListener('load', () => {
  clearTimeout(addButtonsTimeout);
  addButtonsTimeout = setTimeout(() => {
    console.log('DOM fully loaded and parsed');
    main();
    addButtonsToPage(document.body);
  }, 500);
});

document.addEventListener('DOMContentLoaded', () => {
  clearTimeout(addButtonsTimeout);
  addButtonsTimeout = setTimeout(() => {
    addButtonsToPage(document.body);
  }, 500);
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

// 修改获取 YouTube 频道 ID 的函数
const getYoutubeChannelIdFromUrl = (url) => {
  // 首先尝试从 head 中的 link 标签获取
  const channelLink = document.querySelector('link[itemprop="url"][href*="/channel/"]');
  if (channelLink) {
    const match = channelLink.href.match(/\/channel\/(UC[\w-]+)/);
    if (match) {
      return match[1];
    }
  }

  // 如果找不到 link 标签，尝试从 URL 中获取
  const urlMatch = url.match(/\/channel\/(UC[\w-]+)/);
  if (urlMatch) {
    return urlMatch[1];
  }

  return null;
};

// 修改获取 YouTube 频道 URL 的函数
const getChannelUrlFromYoutube = (container) => {
  // 首先尝试从 head 中的 link 标签获取
  const channelLink = document.querySelector('link[itemprop="url"][href*="/channel/"]');
  if (channelLink) {
    return channelLink.href;
  }

  // 从当前 URL 获取（如果在频道页面）
  if (window.location.pathname.includes('/channel/') || 
      window.location.pathname.includes('/@')) {
    return window.location.href.split('?')[0];
  }

  return null;
};

// 添加一个函数来等待元素出现
const waitForElement = (selector, timeout = 5000) => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const checkElement = () => {
      const element = document.querySelector(selector);
      if (element) {
        resolve(element);
        return;
      }

      if (Date.now() - startTime >= timeout) {
        reject(new Error(`Timeout waiting for element: ${selector}`));
        return;
      }

      requestAnimationFrame(checkElement);
    };

    checkElement();
  });
};

// 修改 addSubscribeButtonToYoutube 函数，添加防重复检查
const addSubscribeButtonToYoutube = async (container) => {
  try {
    // 检查是否已经存在我们的按钮
    if (document.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
      console.log('Subscribe button already exists');
      return;
    }

    // 等待订阅按钮容器出现
    const subscribeContainer = await waitForElement(SELECTORS.YOUTUBE.SUBSCRIBE_CONTAINER);
    
    // 再次检查��防止在等待过程中��钮被添加
    if (document.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
      console.log('Subscribe button was added while waiting');
      return;
    }

    console.log('Found subscribe container:', subscribeContainer);

    // 等待频道信息加载
    await waitForElement(SELECTORS.YOUTUBE.CHANNEL_NAME);

    const channelUrl = getChannelUrlFromYoutube(container);
    if (!channelUrl) {
      console.log('Could not find channel URL');
      return;
    }

    const channelId = getYoutubeChannelIdFromUrl(channelUrl);
    if (!channelId) {
      console.log('Could not find channel ID');
      return;
    }

    console.log('Channel URL:', channelUrl);
    console.log('Channel ID:', channelId);

    let isSubscribed = await checkSubscriptionStatus(channelId);
    const buttonText = isSubscribed ? '取消订阅' : '订阅';
    const subscribeButton = createStyledButton(buttonText, SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), async (event) => {
      event.preventDefault(); // 阻止默认行为
      event.stopPropagation(); // 阻止事件冒泡
      
      try {
        if (isSubscribed) {
          await unsubscribe(channelUrl, { channelId });
          isSubscribed = false;
          subscribeButton.textContent = '订阅';
        } else {
          await subscribe(channelUrl, { channelId });
          isSubscribed = true;
          subscribeButton.textContent = '取消订阅';
        }
        
      } catch (error) {
        console.error('Error handling subscription:', error);
      }
    }, SUBSCRIBE_ICON_SVG);

    // 调整按钮样式以匹配 YouTube 的新设计
    Object.assign(subscribeButton.style, {
      backgroundColor: '#0f0f0f',
      color: '#fff',
      marginLeft: '8px',
      height: '36px',
      padding: '0 16px',
      fontSize: '14px',
      fontWeight: '500',
      textTransform: 'uppercase',
      borderRadius: '18px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: 'none',
      cursor: 'pointer'
    });

    // 添加悬停效果
    subscribeButton.addEventListener('mouseover', () => {
      subscribeButton.style.backgroundColor = '#272727';
    });

    subscribeButton.addEventListener('mouseout', () => {
      subscribeButton.style.backgroundColor = '#0f0f0f';
    });

    // 修改按钮插入逻辑
    const targetContainer = subscribeContainer.querySelector(SELECTORS.YOUTUBE.SUBSCRIBE_CONTAINER);
    if (targetContainer) {
      // 创建一个包装容器
      const wrapper = document.createElement('div');
      wrapper.style.display = 'inline-block';
      wrapper.appendChild(subscribeButton);
      
      // 插入包装容器
      targetContainer.appendChild(wrapper);
      console.log('Subscribe button added successfully in wrapper');
    } else {
      subscribeContainer.appendChild(subscribeButton);
      console.log('Subscribe button added successfully directly');
    }

  } catch (error) {
    console.error('Error in addSubscribeButtonToYoutube:', error);
  }
};

// 修改获取 Pornhub 频道 ID 的函数
const getPornhubChannelIdFromUrl = (container) => {
  // 尝试从订阅按钮获取
  const subscribeButton = container.querySelector(SELECTORS.PORNHUB.SUBSCRIBE_BUTTON);
  if (subscribeButton) {
    const subscribeUrl = subscribeButton.getAttribute('data-subscribe-url');
    const friendUrl = subscribeButton.getAttribute('data-friend-url');
    const dataId = subscribeButton.getAttribute('data-id');

    if (subscribeUrl) {
      const match = subscribeUrl.match(/id=([^&]+)/);
      if (match) return match[1];
    }

    if (dataId) {
      return dataId;
    }
  }

  // 如果找不到按钮属性，尝试从 URL 获取
  const url = window.location.href;
  const urlMatch = url.match(/\/(users|model|channels)\/([^\/\?]+)/i);
  return urlMatch ? urlMatch[2] : null;
};

// 修改获取 Pornhub 频道信息的函数
const getPornhubChannelInfo = (container) => {
  const nameElement = container.querySelector(SELECTORS.PORNHUB.CHANNEL_NAME);
  const avatarElement = container.querySelector(SELECTORS.PORNHUB.AVATAR);
  
  return {
    name: nameElement ? nameElement.textContent.trim() : null,
    avatar: avatarElement ? avatarElement.getAttribute('src') : null,
    url: window.location.href.split('?')[0], // 移除查询参数
  };
};

// 修改 Pornhub 订阅按钮的函数
const addSubscribeButtonToPornhub = async (container) => {
  try {
    if (document.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
      return;
    }

    const subscribeContainer = await waitForElement(SELECTORS.PORNHUB.SUBSCRIBE_CONTAINER);
    if (!subscribeContainer) {
      console.log('Could not find subscribe container');
      return;
    }

    const channelInfo = getPornhubChannelInfo(container);
    const channelId = getPornhubChannelIdFromUrl(container);

    if (!channelId || !channelInfo.name) {
      console.log('Could not find channel information');
      return;
    }

    console.log('Channel Info:', channelInfo);
    console.log('Channel ID:', channelId);

    let isSubscribed = await checkSubscriptionStatus(channelId);
    const buttonText = isSubscribed ? '取消订阅' : '订阅';
    const subscribeButton = createStyledButton(buttonText, SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), async (event) => {
      event.preventDefault();
      event.stopPropagation();
      
      try {
        if (isSubscribed) {
          await unsubscribe(channelInfo.url, { 
            channelId,
            name: channelInfo.name,
            avatar: channelInfo.avatar
          });
          isSubscribed = false;
          subscribeButton.textContent = '订阅';
        } else {
          await subscribe(channelInfo.url, {
            channelId,
            name: channelInfo.name,
            avatar: channelInfo.avatar
          });
          isSubscribed = true;
          subscribeButton.textContent = '取消订阅';
        }
      } catch (error) {
        console.error('Error handling subscription:', error);
      }
    }, SUBSCRIBE_ICON_SVG);

    // 调整按钮样式以匹配 Pornhub 风格
    Object.assign(subscribeButton.style, {
      backgroundColor: '#ff9000',
      color: '#000',
      marginLeft: '8px',
      height: '36px',
      padding: '0 16px',
      fontSize: '14px',
      fontWeight: '500',
      borderRadius: '4px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: 'none',
      cursor: 'pointer'
    });

    // 添加悬停效果
    subscribeButton.addEventListener('mouseover', () => {
      subscribeButton.style.backgroundColor = '#ff7000';
    });

    subscribeButton.addEventListener('mouseout', () => {
      subscribeButton.style.backgroundColor = '#ff9000';
    });

    // 将按钮插入到合适的位置
    const existingSubscribeButton = subscribeContainer.querySelector(SELECTORS.PORNHUB.SUBSCRIBE_BUTTON);
    if (existingSubscribeButton) {
      existingSubscribeButton.parentNode.insertBefore(subscribeButton, existingSubscribeButton.nextSibling);
    } else {
      subscribeContainer.appendChild(subscribeButton);
    }
    
    console.log('Subscribe button added successfully');

  } catch (error) {
    console.error('Error in addSubscribeButtonToPornhub:', error);
  }
};

// 修改 addButtonsToPage 函数，添加 Pornhub 支持
const addButtonsToPage = (container) => {
  const isYoutube = window.location.hostname.includes('youtube.com');
  const isBilibili = window.location.hostname.includes('bilibili.com');
  const isPornhub = window.location.hostname.includes('pornhub.com');

  if (isBilibili) {
    addDownloadButtonToBilibili(container);
    addDownloadButtonToBilibiliVideo(container);
    addSubscribeButtonToBilibili(container);
    addSubscribeButtonToBilibiliDetail(container);
  } else if (isYoutube) {
    // 对于 YouTube，我们需要在页面加载完成后添加按钮
    addSubscribeButtonToYoutube(container);
  } else if (isPornhub) {
    addSubscribeButtonToPornhub(container);
  }
};

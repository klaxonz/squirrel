const SELECTORS = {
  BILIBILI: {
    VIDEO_CARD: '.bili-video-card',
    INFO_BOTTOM: '.bili-video-card__info--bottom',
    VIDEO_TOOLBAR: '.video-toolbar-left-main',
    SUBSCRIBE_BUTTON: '.up-info__btn-panel .follow-btn',
    UP_INFO_CONTAINER: '.up-info-container',
  },
  COMMON: {
    DOWNLOAD_BUTTON: '.ytdlp-btn',
    SUBSCRIBE_BUTTON: '.subscribe-btn',
  }
};

const DOWNLOAD_ICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
  <polyline points="7 10 12 15 17 10"></polyline>
  <line x1="12" y1="15" x2="12" y2="3"></line>
</svg>
`;

const createButton = (text, className, clickHandler, useIcon = false) => {
  const button = document.createElement('button');
  if (useIcon) {
    button.innerHTML = DOWNLOAD_ICON_SVG;
    button.title = text;
  } else {
    button.textContent = text;
  }
  button.classList.add(className);
  button.addEventListener('click', clickHandler);
  return button;
};

const download = (url, data) => {
  chrome.runtime.sendMessage({ action: "download", data: { url, ...data } }, (response) => {
    console.log("Download response:", response);
    // 可以在这里添加下载成功或失败的用户反馈
  });
};

const subscribe = (url, data) => {
  chrome.runtime.sendMessage({ action: "subscribe", data: { url, ...data } }, (response) => {
    console.log("Subscribe response:", response);
    // 可以在这里添加订阅成功或失败的用户反馈
  });
};

const addDownloadButtonToBilibili = (shadowRoot) => {
  const videoCards = shadowRoot.querySelectorAll(SELECTORS.BILIBILI.VIDEO_CARD);
  videoCards.forEach(card => {
    if (!card.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON)) {
      const infoBottom = card.querySelector(SELECTORS.BILIBILI.INFO_BOTTOM);
      if (infoBottom) {
        const videoUrl = card.querySelector('a').href;
        const downloadButton = createButton('', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), () => download(videoUrl, {}), true);
        Object.assign(downloadButton.style, {
          backgroundColor: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '0',
          marginLeft: '10px',
        });
        infoBottom.appendChild(downloadButton);
      }
    }
  });
};

const addDownloadButtonToBilibiliVideo = (shadowRoot) => {
  const toolbar = shadowRoot.querySelector(SELECTORS.BILIBILI.VIDEO_TOOLBAR);
  if (toolbar && !toolbar.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON)) {
    const videoUrl = window.location.href;
    const downloadButton = createButton('下载视频', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), () => download(videoUrl, {}));
    Object.assign(downloadButton.style, {
      marginLeft: '10px',
    });
    toolbar.appendChild(downloadButton);
  }
};

const addSubscribeButtonToBilibili = (shadowRoot) => {
  const upInfoContainer = shadowRoot.querySelector(SELECTORS.BILIBILI.UP_INFO_CONTAINER);
  if (upInfoContainer && !upInfoContainer.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
    const channelUrl = getChannelUrlFromBilibili(upInfoContainer);
    if (channelUrl) {
      const subscribeButton = createButton('订阅UP主', SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), () => {
        const channelId = getChannelIdFromUrl(channelUrl);
        subscribe(channelUrl, { channelId });
      });
      Object.assign(subscribeButton.style, {
        marginLeft: '10px',
      });
      const originalSubscribeButton = upInfoContainer.querySelector(SELECTORS.BILIBILI.SUBSCRIBE_BUTTON);
      if (originalSubscribeButton) {
        originalSubscribeButton.parentNode.insertBefore(subscribeButton, originalSubscribeButton.nextSibling);
      } else {
        upInfoContainer.appendChild(subscribeButton);
      }
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

const getChannelIdFromUrl = (url) => {
  const match = url.match(/space\.bilibili\.com\/(\d+)/);
  return match ? match[1] : null;
};

const main = () => {
  const shadowRoot = document.querySelector('#bewly')?.shadowRoot;
  if (shadowRoot) {
    addDownloadButtonToBilibili(shadowRoot);
    addDownloadButtonToBilibiliVideo(shadowRoot);
    addSubscribeButtonToBilibili(shadowRoot);
  }
};

const observeShadowDOM = () => {
  const bewly = document.querySelector('#bewly');
  if (bewly && bewly.shadowRoot) {
    const observer = new MutationObserver(main);
    observer.observe(bewly.shadowRoot, { childList: true, subtree: true });
    main();
  } else {
    setTimeout(observeShadowDOM, 1000);
  }
};

observeShadowDOM();
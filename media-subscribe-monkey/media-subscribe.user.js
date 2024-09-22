// ==UserScript==
// @name         视频下载和订阅 (Shadow DOM 版本)
// @namespace    http://tampermonkey.net/
// @version      0.3
// @description  在特定网站的 Shadow DOM 中执行视频下载和频道订阅操作
// @author       你的名字
// @match        *://*.bilibili.com/*
// @match        *://*.youtube.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_download
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    // 常量定义
    const DEFAULT_HOST = "http://localhost:8000";
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

    // 工具函数
    const getHostConfig = () => GM_getValue('backendHost', DEFAULT_HOST);
    const setHostConfig = (host) => GM_setValue('backendHost', host);

    // 添加下载图标的 SVG
    const DOWNLOAD_ICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
  <polyline points="7 10 12 15 17 10"></polyline>
  <line x1="12" y1="15" x2="12" y2="3"></line>
</svg>
`;

    // 修改 createButton 函数，支持使用图标
    const createButton = (text, className, clickHandler, useIcon = false) => {
        const button = document.createElement('button');
        if (useIcon) {
            button.innerHTML = DOWNLOAD_ICON_SVG;
            button.title = text; // 使用 title 属性显示悬停文本
        } else {
            button.textContent = text;
        }
        button.classList.add(className);
        button.addEventListener('click', clickHandler);
        return button;
    };

    const sendRequest = async (url, data, endpoint) => {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${getHostConfig()}${endpoint}`,
                data: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
                onload: (response) => resolve(response.status === 200),
                onerror: reject,
                ontimeout: reject,
                timeout: 10000
            });
        });
    };

    const download = (url, data) => sendRequest(url, data, '/api/task/download');
    const subscribe = (url, data) => sendRequest(url, data, '/api/channel/subscribe');

    // 获取 Shadow DOM
    const getShadowRoot = () => {
        const bewly = document.querySelector('#bewly');
        return bewly && bewly.shadowRoot;
    };

    // 添加下载按钮到B站视频卡片
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

    // 添加下载按钮到B站视频页面
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

    // 添加订阅按钮到B站
    const addSubscribeButtonToBilibili = (shadowRoot) => {
        const upInfoContainer = shadowRoot.querySelector(SELECTORS.BILIBILI.UP_INFO_CONTAINER);
        if (upInfoContainer && !upInfoContainer.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
            const channelUrl = getChannelUrlFromBilibili(upInfoContainer);
            if (channelUrl) {
                const subscribeButton = createButton('订阅UP主', SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), () => subscribe(channelUrl, {}));
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

    const main = () => {
        const shadowRoot = getShadowRoot();
        if (shadowRoot) {
            if (window.location.hostname.includes('bilibili.com')) {
                addDownloadButtonToBilibili(shadowRoot);
                addDownloadButtonToBilibiliVideo(shadowRoot);
                addSubscribeButtonToBilibili(shadowRoot);
            }
        }
    };

    // 使用 MutationObserver 来监听 Shadow DOM 变化
    const observeShadowDOM = () => {
        const bewly = document.querySelector('#bewly');
        if (bewly && bewly.shadowRoot) {
            const observer = new MutationObserver(main);
            observer.observe(bewly.shadowRoot, { childList: true, subtree: true });
            main(); // 初次运行
        } else {
            setTimeout(observeShadowDOM, 1000); // 如果 Shadow DOM 还没准备好，等待后重试
        }
    };

    // 开始观察
    observeShadowDOM();

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

})();
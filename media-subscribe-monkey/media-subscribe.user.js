// ==UserScript==
// @name         视频下载
// @namespace    http://tampermonkey.net/
// @version      0.1.1
// @description  在特定网站执行视频下载和频道订阅操作
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
        YOUTUBE: {
            VIDEO_CARD: '#dismissible',
            METADATA_LINE: '#metadata-line',
            SUBSCRIBE_BUTTON: '.yt-flexible-actions-view-model-wiz__action',
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

    // UI 相关函数
    const createFloatingButton = () => {
        const button = createButton('Configure Host', 'config-host-btn', showConfigDialog);
        Object.assign(button.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            zIndex: '1000',
            backgroundColor: '#f00',
            color: '#fff',
            padding: '10px 20px',
            borderRadius: '5px',
            border: 'none',
            cursor: 'pointer',
        });
        document.body.appendChild(button);
    };

    const showConfigDialog = () => {
        const dialog = document.createElement('div');
        Object.assign(dialog.style, {
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: '#fff',
            padding: '20px',
            zIndex: '1001',
            boxShadow: '0 0 10px rgba(0, 0, 0, 0.5)',
            borderRadius: '5px',
        });

        const input = document.createElement('input');
        input.type = 'text';
        input.value = getHostConfig();
        input.style.width = '100%';
        input.style.marginBottom = '10px';

        const saveButton = createButton('Save', 'save-config-btn', () => {
            setHostConfig(input.value);
            dialog.remove();
        });

        dialog.appendChild(input);
        dialog.appendChild(saveButton);
        document.body.appendChild(dialog);
    };

    // 主要逻辑函数
    const addDownloadButtonToBilibili = () => {
        const videoCards = document.querySelectorAll(SELECTORS.BILIBILI.VIDEO_CARD);
        videoCards.forEach(card => {
            const infoBottom = card.querySelector(SELECTORS.BILIBILI.INFO_BOTTOM);
            if (infoBottom && !infoBottom.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON)) {
                const downloadButton = createButton('下载视频', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), (event) => {
                    event.preventDefault();
                    const videoUrl = card.querySelector('.bili-video-card__image--link').getAttribute('href');
                    download(videoUrl, { url: videoUrl });
                }, true); // 使用图标
                
                // 设置按钮样式
                Object.assign(downloadButton.style, {
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '8px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#757575', // 使用哔哩哔哩的灰色
                });
                
                infoBottom.appendChild(downloadButton);
            }
        });
    };

    const addDownloadButtonToBilibiliVideo = async () => {
        const element = await getElement(document, SELECTORS.BILIBILI.VIDEO_TOOLBAR, 10000);
        if (element && !element.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON)) {
            const downloadButton = createButton('下载', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), () => {
                const url = window.location.href;
                download(url, { url });
            }, true); // 使用图标
            
            // 设置按钮样式
            Object.assign(downloadButton.style, {
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '8px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#757575', // 使用哔哩哔哩的灰色
            });
            
            element.appendChild(downloadButton);
        }
    };

    const addDownloadButtonToYoutube = async () => {
        const videoCards = document.querySelectorAll(SELECTORS.YOUTUBE.VIDEO_CARD);
        videoCards.forEach(card => {
            const bottomEl = card.querySelector(SELECTORS.YOUTUBE.METADATA_LINE);
            if (bottomEl) {
                const existingBtn = bottomEl.querySelector(SELECTORS.COMMON.DOWNLOAD_BUTTON);
                if (existingBtn) {
                    bottomEl.removeChild(existingBtn);
                }

                const downloadButton = createButton('下载', SELECTORS.COMMON.DOWNLOAD_BUTTON.slice(1), (event) => {
                    event.stopPropagation();
                    const href = card.querySelector("a.ytd-thumbnail").getAttribute("href");
                    const url = `${window.location.origin}${href}`;
                    download(url, { url });
                });
                bottomEl.appendChild(downloadButton);
            }
        });
    };

    const addSubscribeButtonToYoutube = async () => {
        const element = await getElement(document, SELECTORS.YOUTUBE.SUBSCRIBE_BUTTON, 10000);
        if (element && !element.parentNode.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
            let url = window.location.href.replace(/\/(videos|featured)/, '');
            const subscribeButton = createButton('立即订阅', SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), (event) => {
                event.stopPropagation();
                subscribe(url, { url });
            });
            Object.assign(subscribeButton.style, {
                cursor: 'pointer',
                margin: '0 0 0 4px',
                color: 'white',
            });
            element.parentNode.appendChild(subscribeButton);
        }
    };

    const addSubscribeButtonToBilibili = async () => {
        const element = await getElement(document, SELECTORS.BILIBILI.UP_INFO_CONTAINER, 10000);
        if (element && !element.querySelector(SELECTORS.COMMON.SUBSCRIBE_BUTTON)) {
            const channelUrl = getChannelUrlFromBilibili(element);
            console.log('Bilibili channel URL:', channelUrl); // 添加这行日志
            if (!channelUrl) return;

            const subscribeButton = createButton('订阅', SELECTORS.COMMON.SUBSCRIBE_BUTTON.slice(1), (event) => {
                event.stopPropagation();
                subscribe(channelUrl, { url: channelUrl });
            });
            
            // 设置订阅按钮样式
            Object.assign(subscribeButton.style, {
                padding: '0 12px',
                height: '34px',
                lineHeight: '34px',
                fontSize: '14px',
                borderRadius: '4px',
                cursor: 'pointer',
                backgroundColor: '#00a1d6',
                color: '#fff',
                border: 'none',
                marginRight: '10px',
            });
            
            const btnPanel = element.querySelector('.up-info__btn-panel');
            if (btnPanel) {
                // 获取所有现有的按钮
                const existingButtons = btnPanel.querySelectorAll('.default-btn');
                
                // 移除所有现有的按钮
                existingButtons.forEach(btn => btn.remove());
                
                // 添加订阅按钮作为第一个按钮
                btnPanel.appendChild(subscribeButton);
                
                // 重新添加其他按钮，并调整它们的样式
                existingButtons.forEach(btn => {
                    Object.assign(btn.style, {
                        padding: '0 12px',
                        height: '34px',
                        lineHeight: '34px',
                        fontSize: '14px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        backgroundColor: '#f4f4f4',
                        color: '#505050',
                        border: 'none',
                        marginRight: '10px',
                    });
                    btnPanel.appendChild(btn);
                });
                
                // 确保按钮面板是flex布局
                Object.assign(btnPanel.style, {
                    display: 'flex',
                    alignItems: 'center',
                });
            }
        }
    };

    // 初始化
    createFloatingButton();

    // 定时器
    setInterval(() => {
        if (window.location.hostname.includes('bilibili.com')) {
            addDownloadButtonToBilibili();
            addDownloadButtonToBilibiliVideo();
            addSubscribeButtonToBilibili();
        } else if (window.location.hostname.includes('youtube.com')) {
            addDownloadButtonToYoutube();
            addSubscribeButtonToYoutube();
        }
    }, 1000);

    const getElement = (parent, selector, timeout = 0) => {
      return new Promise(resolve => {
        let result = parent.querySelector(selector);
        if (result) return resolve(result);
        let timer;
        const mutationObserver = window.MutationObserver || window.WebkitMutationObserver || window.MozMutationObserver;
        if (mutationObserver) {
          const observer = new mutationObserver(mutations => {
            for (let mutation of mutations) {
              for (let addedNode of mutation.addedNodes) {
                if (addedNode instanceof Element) {
                  result = addedNode.matches(selector) ? addedNode : addedNode.querySelector(selector);
                  if (result) {
                    observer.disconnect();
                    timer && clearTimeout(timer);
                    return resolve(result);
                  }
                }
              }
            }
          });
          observer.observe(parent, {
            childList: true,
            subtree: true
          });
          if (timeout > 0) {
            timer = setTimeout(() => {
              observer.disconnect();
              return resolve(null);
            }, timeout);
          }
        } else {
          const listener = e => {
            if (e.target instanceof Element) {
              result = e.target.matches(selector) ? e.target : e.target.querySelector(selector);
              if (result) {
                parent.removeEventListener('DOMNodeInserted', listener, true);
                timer && clearTimeout(timer);
                return resolve(result);
              }
            }
          };
          parent.addEventListener('DOMNodeInserted', listener, true);
          if (timeout > 0) {
            timer = setTimeout(() => {
              parent.removeEventListener('DOMNodeInserted', listener, true);
              return resolve(null);
            }, timeout);
          }
        }
      });
    }

    const main = () => {
        if (window.location.hostname.includes('bilibili.com')) {
            addDownloadButtonToBilibili();
            addDownloadButtonToBilibiliVideo();
            addSubscribeButtonToBilibili();
        } else if (window.location.hostname.includes('youtube.com')) {
            addDownloadButtonToYoutube();
            addSubscribeButtonToYoutube();
        }
    };

    // 使用 MutationObserver 来监听 DOM 变化
    const observer = new MutationObserver(main);
    observer.observe(document.body, { childList: true, subtree: true });

    // 初次运行
    main();

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
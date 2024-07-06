// ==UserScript==
// @name         视频下载
// @namespace    http://tampermonkey.net/
// @version      0.1.0
// @description  尝试在访问特定网站时执行操作
// @author       你的名字
// @match        *://*.bilibili.com/*
// @match        *://*.youtube.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_download
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

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

    const download = (url, data) => {
      GM_xmlhttpRequest({
          method: 'POST',
          url: 'http://127.0.0.1:8000/api/task/download',
          data: data,
          headers: {
              "Content-Type": "application/json"
          },
          onload: function(response) {
              if (response.status === 200) {
                  console.log('下载任务已启动');
              } else {
                  console.log('下载任务启动失败');
              }
          },
          onerror: function(response) {
              console.error('下载请求出错:', response.statusText);
          },
          ontimeout: function(response) {
              console.error('下载请求超时');
          },
          timeout: 10000
      });
    };

    const subscribe = (url, data) => {
      GM_xmlhttpRequest({
          method: 'POST',
          url: 'http://127.0.0.1:8000/api/channel/subscribe',
          data: data,
          headers: {
              "Content-Type": "application/json"
          },
          onload: function(response) {
              if (response.status === 200) {
                  console.log('订阅成功');
              } else {
                  console.log('订阅失败');
              }
          },
          onerror: function(response) {
              console.error('订阅失败:', response.statusText);
          },
          ontimeout: function(response) {
              console.error('订阅失败');
          },
          timeout: 10000
      });
    };

    const createDownloadButton = () => {
        // 创建下载按钮元素
        const downloadButton = document.createElement('button');
        downloadButton.textContent = '下载视频';
        downloadButton.style.padding = '5px 10px';
        downloadButton.style.cursor = 'pointer';
        downloadButton.style.border = 'none';
        downloadButton.style.borderRadius = '5px';
        downloadButton.classList.add('ytdlp-btn');

        // 点击按钮发送请求的函数
        downloadButton.addEventListener('click', function(event) {
            event.preventDefault(); // 阻止链接默认的跳转行为
            const videoCard = event.target.closest('.bili-video-card');
            if (videoCard) {
                const videoUrl = videoCard.querySelector('.bili-video-card__image--link').getAttribute('href');
                const downloadData = JSON.stringify({ url: videoUrl });
                download(videoUrl, downloadData);
            }
        });

        return downloadButton;
    }


    // Bilibili 首页
    setInterval(() => {
      // 寻找页面上所有的视频卡片，并添加下载按钮
      const videoCards = document.querySelectorAll('.bili-video-card');
      videoCards.forEach(card => {
          const infoBottom = card.querySelector('.bili-video-card__info--bottom');
          if (infoBottom) {
              const addedBtn = infoBottom.querySelector('.ytdlp-btn');
              if (addedBtn) {
                return;
              }
              const downloadButton = createDownloadButton();
              infoBottom.appendChild(downloadButton);
          }
      });
    }, 1000)

    // 视频播放页
    setTimeout(() => {
      getElement(document, '.video-toolbar-left-main', 10000).then(element => {
          if(!element) {
              return;
          }
          const div = document.createElement('div');
          div.classList.add('toolbar-left-item-wrap');
          div.textContent = '下载';
          div.style.cursor = 'pointer';

          // 点击按钮发送请求的函数
          div.addEventListener('click', function(event) {
              const url = window.location.href;
              const data = JSON.stringify({ url: url });
              download(url, data);
          });

          element.appendChild(div);
      });
    }, 5000);

    setInterval(() => {
        getElement(document, '#dismissible', 10000).then(element => {
            const bilibiliVideoCards = document.querySelectorAll('#dismissible');
            bilibiliVideoCards.forEach(card => {
                const btn = card.querySelector(".ytdlp-btn");

                const bottomEl = card.querySelector("#metadata-line");
                if (!bottomEl) {
                  return
                }
                if (btn) {
                  bottomEl.removeChild(btn);
                }

                const span = document.createElement('span');
                span.textContent = '下载';
                span.style.cursor = 'pointer';
                span.style.margin = '0 0 0 4px';
                span.classList.add('ytdlp-btn');

                const host = window.location.href;
                const href = card.querySelector("a.ytd-thumbnail").getAttribute("href");
                const url = host + href;

                // 点击按钮发送请求的函数
                span.addEventListener('click', function(event) {
                    event.stopPropagation();
                    const data = JSON.stringify({ url: url });
                    download(url, data);
                });
                bottomEl.appendChild(span);
            });
        });
    }, 1000);

    // 订阅
    setInterval(() => {
        getElement(document, '.yt-flexible-actions-view-model-wiz__action', 10000).then(element => {
            let el = document.querySelector('.yt-flexible-actions-view-model-wiz__action');
            if (!el) {
              return;
            }
            el = el.parentNode;
            console.log('sss', el);

            const btn = el.querySelector(".subscribe-btn");
            if (btn) {
              return;
            }

            const span = document.createElement('span');
            span.textContent = '立即订阅';
            span.style.cursor = 'pointer';
            span.style.margin = '0 0 0 4px';
            span.style.color = 'white';
            span.classList.add('subscribe-btn');

            let url = window.location.href;
            if (url.includes("/videos")) {
              url = url.replace("/videos", "");
            }
            if (url.includes("/featured")) {
              url = url.replace("/featured", "");
            }
            // 点击按钮发送请求的函数
            span.addEventListener('click', function(event) {
                event.stopPropagation();
                const data = JSON.stringify({ url: url });
                subscribe(url, data);
            });
            el.appendChild(span);
        });
    }, 1000);

    setInterval(() => {
        getElement(document, '.h-action', 10000).then(element => {
            let el = document.querySelector('.h-action');
            if (!el) {
              return;
            }

            const btn = el.querySelector(".subscribe-btn");
            if (btn) {
              return;
            }

            const span = document.createElement('span');
            span.textContent = '立即订阅';
            span.style.cursor = 'pointer';
            span.style.margin = '0 0 0 4px';
            span.style.color = 'white';
            span.classList.add('subscribe-btn');
            span.classList.add('h-f-btn');

            let url = window.location.href;
            url = url.split('?')[0];
            // 点击按钮发送请求的函数
            span.addEventListener('click', function(event) {
                event.stopPropagation();
                const data = JSON.stringify({ url: url });
                subscribe(url, data);
            });
            el.appendChild(span);
        });
    }, 1000);


})();
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ backendHost: "http://localhost:8000" }, () => {
    console.log("Default backend host set");
  });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "download") {
    chrome.storage.sync.get('backendHost', (data) => {
      fetch(`${data.backendHost}/api/task/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request.data),
      })
      .then(response => response.json())
      .then(data => sendResponse({ success: true, data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    });
    return true;  // 保持消息通道开放
  } else if (request.action === "subscribe") {
    chrome.storage.sync.get('backendHost', (data) => {
      fetch(`${data.backendHost}/api/channel/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request.data),
      })
      .then(response => response.json())
      .then(data => sendResponse({ success: true, data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    });
    return true;  // 保持消息通道开放
  }
});
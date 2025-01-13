chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ backendHost: "http://localhost:8000" }, () => {
    console.log("Default backend host set");
  });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  chrome.storage.sync.get('backendHost', (data) => {
    const backendHost = data.backendHost;

    switch (request.action) {
      case "download":
        handleDownload(backendHost, request.data, sendResponse);
        break;
      case "subscribe":
        handleSubscribe(backendHost, request.data, sendResponse);
        break;
      case "unsubscribe":
        handleUnsubscribe(backendHost, request.data, sendResponse);
        break;
      case "checkSubscription":
        handleCheckSubscription(backendHost, request.data, sendResponse);
        break;
      default:
        sendResponse({ success: false, error: "Unknown action" });
    }
  });
  return true;
});

function handleDownload(backendHost, data, sendResponse) {
  fetch(`${backendHost}/api/task/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  .then(response => response.json())
  .then(data => sendResponse({ success: true, data }))
  .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleSubscribe(backendHost, data, sendResponse) {
  fetch(`${backendHost}/api/subscription/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  .then(response => response.json())
  .then(data => sendResponse({ success: true, data }))
  .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleUnsubscribe(backendHost, data, sendResponse) {
  fetch(`${backendHost}/api/subscription/unsubscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  .then(response => response.json())
  .then(data => sendResponse({ success: true, data }))
  .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleCheckSubscription(backendHost, data, sendResponse) {
  fetch(`${backendHost}/api/subscription/status?url=${data.url}`)
    .then(response => response.json())
    .then(data => {
      console.log("API response for subscription status:", data);
      sendResponse({ 
        success: true, 
        data: {
          isSubscribed: data.data.is_subscribed
        }
      });
    })
    .catch(error => {
      console.error("Error in handleCheckSubscription:", error);
      sendResponse({ success: false, error: error.message });
    });
}
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ backendHost: "http://localhost:8000" }, () => {
    console.log("Default backend host set");
  });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  chrome.storage.sync.get('backendHost', async (data) => {
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
      case "login":
        handleLogin(backendHost, request.data, sendResponse);
        break;
      case "logout":
        handleLogout(sendResponse);
        break;
      default:
        sendResponse({ success: false, error: "Unknown action" });
    }
  });
  return true;
});

async function addAuthHeaders(headers) {
  const data = await chrome.storage.sync.get('token');
  if (data.token) {
    headers['Authorization'] = `Bearer ${data.token}`;
  }
  return headers;
}

async function handleDownload(backendHost, data, sendResponse) {
  const headers = await addAuthHeaders({ 'Content-Type': 'application/json' });
  
  fetch(`${backendHost}/api/task/download`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  })
  .then(response => {
    if (response.status === 401) {
      throw new Error('请先登录');
    }
    return response.json();
  })
  .then(data => sendResponse({ success: true, data }))
  .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleSubscribe(backendHost, data, sendResponse) {
  addAuthHeaders({ 'Content-Type': 'application/json' })
    .then(headers => {
      return fetch(`${backendHost}/api/subscription/subscribe`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });
    })
    .then(response => {
      if (response.status === 401) {
        throw new Error('请先登录');
      }
      return response.json();
    })
    .then(data => sendResponse({ success: true, data }))
    .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleUnsubscribe(backendHost, data, sendResponse) {
  addAuthHeaders({ 'Content-Type': 'application/json' })
    .then(headers => {
      return fetch(`${backendHost}/api/subscription/unsubscribe`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });
    })
    .then(response => {
      if (response.status === 401) {
        throw new Error('请先登录');
      }
      return response.json();
    })
    .then(data => sendResponse({ success: true, data }))
    .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleCheckSubscription(backendHost, data, sendResponse) {
  addAuthHeaders({ 'Content-Type': 'application/json' })
    .then(headers => {
      return fetch(`${backendHost}/api/subscription/status?url=${encodeURIComponent(data.url)}`, {
        headers
      });
    })
    .then(response => {
      if (response.status === 401) {
        throw new Error('请先登录');
      }
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
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

function handleLogin(backendHost, data, sendResponse) {
  fetch(`${backendHost}/api/users/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  .then(response => response.json())
  .then(data => {
    if (data.code === 0 && data.data.access_token) {
      chrome.storage.sync.set({ token: data.data.access_token }, () => {
        sendResponse({ success: true });
      });
    } else {
      throw new Error(data.msg || '登录失败');
    }
  })
  .catch(error => sendResponse({ success: false, error: error.message }));
}

function handleLogout(sendResponse) {
  chrome.storage.sync.remove('token', () => {
    sendResponse({ success: true });
  });
}
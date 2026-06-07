chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ backendHost: 'http://localhost:8000' })
})

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  chrome.storage.sync.get('backendHost', async (data) => {
    const backendHost = data.backendHost

    switch (request.action) {
      case 'download':
        await handleDownload(backendHost, request.data, sendResponse)
        break
      case 'subscribe':
        await handleSubscribe(backendHost, request.data, sendResponse)
        break
      case 'unsubscribe':
        await handleUnsubscribe(backendHost, request.data, sendResponse)
        break
      case 'checkSubscription':
        await handleCheckSubscription(backendHost, request.data, sendResponse)
        break
      case 'login':
        await handleLogin(backendHost, request.data, sendResponse)
        break
      case 'logout':
        handleLogout(sendResponse)
        break
      default:
        sendResponse({ success: false, error: 'Unknown action' })
    }
  })
  return true
})

async function addAuthHeaders(headers) {
  const data = await chrome.storage.sync.get('token')
  if (data.token) {
    headers['Authorization'] = `Bearer ${data.token}`
  }
  return headers
}

async function handleDownload(backendHost, data, sendResponse) {
  try {
    const headers = await addAuthHeaders({ 'Content-Type': 'application/json' })
    const response = await fetch(`${backendHost}/api/task/download`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })
    if (response.status === 401) {
      throw new Error('请先登录')
    }
    const result = await response.json()
    sendResponse({ success: true, data: result })
  } catch (error) {
    sendResponse({ success: false, error: error.message })
  }
}

async function handleSubscribe(backendHost, data, sendResponse) {
  try {
    const headers = await addAuthHeaders({ 'Content-Type': 'application/json' })
    const response = await fetch(`${backendHost}/api/subscription/subscribe`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })
    if (response.status === 401) {
      throw new Error('请先登录')
    }
    const result = await response.json()
    sendResponse({ success: true, data: result })
  } catch (error) {
    sendResponse({ success: false, error: error.message })
  }
}

async function handleUnsubscribe(backendHost, data, sendResponse) {
  try {
    const headers = await addAuthHeaders({ 'Content-Type': 'application/json' })
    const response = await fetch(`${backendHost}/api/subscription/unsubscribe`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })
    if (response.status === 401) {
      throw new Error('请先登录')
    }
    const result = await response.json()
    sendResponse({ success: true, data: result })
  } catch (error) {
    sendResponse({ success: false, error: error.message })
  }
}

async function handleCheckSubscription(backendHost, data, sendResponse) {
  try {
    const headers = await addAuthHeaders({ 'Content-Type': 'application/json' })
    const response = await fetch(`${backendHost}/api/subscription/status?url=${encodeURIComponent(data.url)}`, {
      headers
    })
    if (response.status === 401) {
      throw new Error('请先登录')
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const result = await response.json()
    sendResponse({
      success: true,
      data: {
        isSubscribed: result.data.is_subscribed
      }
    })
  } catch (error) {
    console.error('Error in handleCheckSubscription:', error)
    sendResponse({ success: false, error: error.message })
  }
}

async function handleLogin(backendHost, data, sendResponse) {
  try {
    const response = await fetch(`${backendHost}/api/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    const result = await response.json()
    if (result.code === 0 && result.data.access_token) {
      chrome.storage.sync.set({ token: result.data.access_token }, () => {
        sendResponse({ success: true })
      })
    } else {
      throw new Error(result.msg || '登录失败')
    }
  } catch (error) {
    sendResponse({ success: false, error: error.message })
  }
}

function handleLogout(sendResponse) {
  chrome.storage.sync.remove('token', () => {
    sendResponse({ success: true })
  })
}

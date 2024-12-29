function showStatus(message, isError = false) {
  const status = document.getElementById('status');
  status.textContent = message;
  status.style.display = 'block';
  status.className = `status ${isError ? 'error' : 'success'}`;
  
  setTimeout(() => {
    status.style.display = 'none';
  }, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
  const backendHostInput = document.getElementById('backendHost');
  const saveButton = document.getElementById('saveButton');

  // 加载设置
  chrome.storage.sync.get('backendHost', (data) => {
    backendHostInput.value = data.backendHost || 'http://localhost:8000';
  });

  // 保存设置
  saveButton.addEventListener('click', () => {
    const newBackendHost = backendHostInput.value;
    chrome.storage.sync.set({ backendHost: newBackendHost }, () => {
      showStatus('设置已保存');
    });
  });
}); 
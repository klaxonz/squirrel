document.addEventListener('DOMContentLoaded', () => {
  const backendHostInput = document.getElementById('backendHost');
  const saveButton = document.getElementById('saveButton');

  chrome.storage.sync.get('backendHost', (data) => {
    backendHostInput.value = data.backendHost || 'http://localhost:8000';
  });

  saveButton.addEventListener('click', () => {
    const newBackendHost = backendHostInput.value;
    chrome.storage.sync.set({ backendHost: newBackendHost }, () => {
      console.log('后端主机已保存');
      // 添加视觉反馈
      saveButton.textContent = '已保存';
      setTimeout(() => {
        saveButton.textContent = '保存';
      }, 2000);
    });
  });
});
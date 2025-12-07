// 键盘快捷键组合函数：封装快捷键映射、执行与反馈
// store: Pinia player store
// callbacks: 播放器控制函数

import { ref } from 'vue';

export default function useKeyboardShortcuts(store, callbacks) {
  const keyboardFeedbackTimer = ref(null);

  const showKeyboardFeedback = (message) => {
    store.keyboardFeedback = message;
    store.showKeyboardFeedback = true;

    if (keyboardFeedbackTimer.value) {
      clearTimeout(keyboardFeedbackTimer.value);
    }

    keyboardFeedbackTimer.value = setTimeout(() => {
      store.showKeyboardFeedback = false;
    }, 1500);
  };

  const keyboardShortcuts = {
    ' ': { action: 'togglePlay', description: '播放/暂停' },
    'k': { action: 'togglePlay', description: '播放/暂停' },
    'ArrowRight': { action: 'skipForward5', description: '快进5秒' },
    'ArrowLeft': { action: 'skipBackward5', description: '快退5秒' },
    'j': { action: 'skipBackward10', description: '快退10秒' },
    'l': { action: 'skipForward10', description: '快进10秒' },
    'm': { action: 'toggleMute', description: '静音/取消静音' },
    'ArrowUp': { action: 'volumeUp', description: '音量+5%' },
    'ArrowDown': { action: 'volumeDown', description: '音量-5%' },
    '<': { action: 'decreaseSpeed', description: '减慢播放速度' },
    '>': { action: 'increaseSpeed', description: '加快播放速度' },
    'f': { action: 'toggleFullscreen', description: '全屏/退出全屏' },
    'i': { action: 'togglePictureInPicture', description: '画中画' },
    'c': { action: 'toggleSubtitles', description: '字幕开/关' },
    'C': { action: 'nextSubtitle', description: '切换下一条字幕' },
    'Home': { action: 'jumpToStart', description: '跳转到开始' },
    'End': { action: 'jumpToEnd', description: '跳转到结束' },
    '0': { action: 'jumpToPercent', args: [0], description: '跳转到0%' },
    '1': { action: 'jumpToPercent', args: [10], description: '跳转到10%' },
    '2': { action: 'jumpToPercent', args: [20], description: '跳转到20%' },
    '3': { action: 'jumpToPercent', args: [30], description: '跳转到30%' },
    '4': { action: 'jumpToPercent', args: [40], description: '跳转到40%' },
    '5': { action: 'jumpToPercent', args: [50], description: '跳转到50%' },
    '6': { action: 'jumpToPercent', args: [60], description: '跳转到60%' },
    '7': { action: 'jumpToPercent', args: [70], description: '跳转到70%' },
    '8': { action: 'jumpToPercent', args: [80], description: '跳转到80%' },
    '9': { action: 'jumpToPercent', args: [90], description: '跳转到90%' },
    '?': { action: 'showKeyboardHelp', description: '显示快捷键帮助' },
    'Escape': { action: 'handleEscape', description: '退出菜单/全屏' }
  };

  const executeKeyboardAction = (action, args = []) => {
    const {
      togglePlay,
      skipForward,
      skipBackward,
      setVideoTime,
      toggleMute,
      adjustVolume,
      adjustPlaybackRate,
      toggleFullscreen,
      togglePictureInPicture,
      toggleSubtitles,
      nextSubtitle,
      toggleKeyboardHelp,
      handleEscapeKey,
      getDuration,
      getCurrentTime
    } = callbacks;

    switch (action) {
      case 'togglePlay':
        togglePlay();
        break;
      case 'skipForward':
        skipForward();
        break;
      case 'skipBackward':
        skipBackward();
        break;
      case 'skipForward5': {
        const current = getCurrentTime();
        const duration = getDuration();
        setVideoTime(Math.min(current + 5, duration));
        break;
      }
      case 'skipBackward5': {
        const current = getCurrentTime();
        setVideoTime(Math.max(current - 5, 0));
        break;
      }
      case 'skipForward10': {
        const current = getCurrentTime();
        const duration = getDuration();
        setVideoTime(Math.min(current + 10, duration));
        break;
      }
      case 'skipBackward10': {
        const current = getCurrentTime();
        setVideoTime(Math.max(current - 10, 0));
        break;
      }
      case 'toggleMute':
        toggleMute();
        break;
      case 'volumeUp':
        adjustVolume(5);
        break;
      case 'volumeDown':
        adjustVolume(-5);
        break;
      case 'decreaseSpeed':
        adjustPlaybackRate(-0.25);
        break;
      case 'increaseSpeed':
        adjustPlaybackRate(0.25);
        break;
      case 'toggleFullscreen':
        toggleFullscreen();
        break;
      case 'togglePictureInPicture':
        togglePictureInPicture();
        break;
      case 'toggleSubtitles':
        toggleSubtitles();
        break;
      case 'nextSubtitle':
        if (typeof nextSubtitle === 'function') nextSubtitle();
        break;
      case 'jumpToStart':
        setVideoTime(0);
        break;
      case 'jumpToEnd': {
        const duration = getDuration();
        setVideoTime(duration);
        break;
      }
      case 'jumpToPercent': {
        const percent = args[0] || 0;
        const duration = getDuration();
        setVideoTime((duration * percent) / 100);
        break;
      }
      case 'showKeyboardHelp':
        toggleKeyboardHelp();
        break;
      case 'handleEscape':
        handleEscapeKey();
        break;
    }
  };

  const handleKeyDown = (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    const shortcut = keyboardShortcuts[e.key];
    if (shortcut) {
      e.preventDefault();
      executeKeyboardAction(shortcut.action, shortcut.args);
      showKeyboardFeedback(shortcut.description);
    }
  };

  const cleanup = () => {
    if (keyboardFeedbackTimer.value) {
      clearTimeout(keyboardFeedbackTimer.value);
      keyboardFeedbackTimer.value = null;
    }
  };

  return { handleKeyDown, cleanup };
}

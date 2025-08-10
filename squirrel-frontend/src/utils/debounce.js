// 通用防抖函数，带 cancel 能力
// 使用方式：
// import { debounce } from './debounce'
// const debounced = debounce(fn, delay)
// debounced.cancel()

export function debounce(fn, delay = 100) {
  let timer = null;

  function clearTimer() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  const debouncedFn = function (...args) {
    clearTimer();

    // 针对 MouseEvent 复制必要字段，避免异步后失效
    const firstArg = args[0];
    let safeEventArg = firstArg;
    if (firstArg && typeof firstArg === 'object' && firstArg.type === 'mousemove') {
      safeEventArg = {
        clientX: firstArg.clientX,
        clientY: firstArg.clientY,
        currentTarget: firstArg.currentTarget,
        target: firstArg.target,
      };
      args[0] = safeEventArg;
    }

    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };

  debouncedFn.cancel = clearTimer;

  return debouncedFn;
}

export default debounce;


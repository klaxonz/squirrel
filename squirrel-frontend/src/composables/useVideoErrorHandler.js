import { ref, reactive } from 'vue';
import { Logger } from '../utils/logger'

export default function useVideoErrorHandler() {
  // 错误状态
  const errorState = reactive({
    hasError: false,
    errorType: null,
    errorMessage: '',
    errorCode: null,
    retryCount: 0,
    maxRetries: 3,
    canRetry: true,
    lastErrorTime: null,
    errorDetails: null
  });

  // 错误类型定义
  const ERROR_TYPES = {
    NETWORK: 'network',
    MEDIA: 'media',
    PERMISSION: 'permission',
    UNSUPPORTED: 'unsupported',
    TIMEOUT: 'timeout',
    UNKNOWN: 'unknown'
  };

  // 错误消息映射
  const ERROR_MESSAGES = {
    [ERROR_TYPES.NETWORK]: {
      title: '网络连接错误',
      message: '无法连接到服务器，请检查您的网络连接',
      suggestions: ['检查网络连接', '刷新页面重试', '稍后再试']
    },
    [ERROR_TYPES.MEDIA]: {
      title: '媒体播放错误',
      message: '视频无法播放，可能是格式不支持或文件损坏',
      suggestions: ['尝试其他播放质量', '刷新页面重试', '联系技术支持']
    },
    [ERROR_TYPES.PERMISSION]: {
      title: '权限错误',
      message: '没有播放权限或内容不可用',
      suggestions: ['检查登录状态', '确认访问权限', '联系管理员']
    },
    [ERROR_TYPES.UNSUPPORTED]: {
      title: '不支持的格式',
      message: '您的浏览器不支持此视频格式',
      suggestions: ['更新浏览器', '尝试其他浏览器', '下载支持的播放器']
    },
    [ERROR_TYPES.TIMEOUT]: {
      title: '加载超时',
      message: '视频加载时间过长，请重试',
      suggestions: ['检查网络速度', '刷新页面重试', '稍后再试']
    },
    [ERROR_TYPES.UNKNOWN]: {
      title: '未知错误',
      message: '发生了未知错误，请重试',
      suggestions: ['刷新页面重试', '清除浏览器缓存', '联系技术支持']
    }
  };

  // 处理错误
  const handleError = (error, context = {}) => {
    Logger.error('Video error occurred', error, context);
    
    const errorType = determineErrorType(error);
    const errorInfo = ERROR_MESSAGES[errorType];
    
    errorState.hasError = true;
    errorState.errorType = errorType;
    errorState.errorMessage = errorInfo.message;
    errorState.errorCode = error.code || null;
    errorState.lastErrorTime = Date.now();
    errorState.errorDetails = {
      originalError: error,
      context,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      url: window.location.href
    };
    
    // 判断是否可以重试
    errorState.canRetry = isRetryable(errorType, error);
    
    // 自动重试逻辑
    if (errorState.canRetry && errorState.retryCount < errorState.maxRetries) {
      scheduleRetry(context);
    }
    
    return errorInfo;
  };

  // 确定错误类型
  const determineErrorType = (error) => {
    if (!error) return ERROR_TYPES.UNKNOWN;
    
    // 网络错误
    if (error.name === 'NetworkError' || 
        error.message?.includes('network') ||
        error.code === 2) {
      return ERROR_TYPES.NETWORK;
    }
    
    // 媒体错误
    if (error.name === 'MediaError' ||
        error.code === 3 || error.code === 4) {
      return ERROR_TYPES.MEDIA;
    }
    
    // 权限错误
    if (error.code === 1 || 
        error.message?.includes('permission') ||
        error.message?.includes('forbidden')) {
      return ERROR_TYPES.PERMISSION;
    }
    
    // 不支持的格式
    if (error.message?.includes('unsupported') ||
        error.message?.includes('format')) {
      return ERROR_TYPES.UNSUPPORTED;
    }
    
    // 超时错误
    if (error.name === 'TimeoutError' ||
        error.message?.includes('timeout')) {
      return ERROR_TYPES.TIMEOUT;
    }
    
    return ERROR_TYPES.UNKNOWN;
  };

  // 判断是否可以重试
  const isRetryable = (errorType, error) => {
    const nonRetryableTypes = [ERROR_TYPES.PERMISSION, ERROR_TYPES.UNSUPPORTED];
    
    if (nonRetryableTypes.includes(errorType)) {
      return false;
    }
    
    // 某些特定错误码不可重试
    if (error.code === 1) { // MEDIA_ERR_ABORTED
      return false;
    }
    
    return true;
  };

  // 安排重试
  const scheduleRetry = (context) => {
    const retryDelay = Math.min(1000 * Math.pow(2, errorState.retryCount), 10000);
    
    setTimeout(() => {
      retry(context);
    }, retryDelay);
  };

  // 重试操作
  const retry = (context = {}) => {
    if (errorState.retryCount >= errorState.maxRetries) {
      Logger.warn('Max retry attempts reached');
      return false;
    }
    
    errorState.retryCount++;
    Logger.debug(`Retrying... Attempt ${errorState.retryCount}/${errorState.maxRetries}`);
    
    // 清除错误状态
    clearError();
    
    // 执行重试回调
    if (context.retryCallback && typeof context.retryCallback === 'function') {
      context.retryCallback();
    }
    
    return true;
  };

  // 手动重试
  const manualRetry = (retryCallback) => {
    if (!errorState.canRetry) {
      Logger.warn('This error is not retryable');
      return false;
    }
    
    return retry({ retryCallback });
  };

  // 清除错误状态
  const clearError = () => {
    errorState.hasError = false;
    errorState.errorType = null;
    errorState.errorMessage = '';
    errorState.errorCode = null;
    errorState.errorDetails = null;
  };

  // 重置重试计数
  const resetRetryCount = () => {
    errorState.retryCount = 0;
  };

  // 获取错误信息
  const getErrorInfo = () => {
    if (!errorState.hasError) return null;
    
    return {
      ...ERROR_MESSAGES[errorState.errorType],
      code: errorState.errorCode,
      retryCount: errorState.retryCount,
      maxRetries: errorState.maxRetries,
      canRetry: errorState.canRetry,
      lastErrorTime: errorState.lastErrorTime
    };
  };

  // 报告错误（发送到服务器）
  const reportError = async (additionalInfo = {}) => {
    if (!errorState.hasError) return;
    
    try {
      const errorReport = {
        ...errorState.errorDetails,
        ...additionalInfo,
        retryCount: errorState.retryCount,
        resolved: false
      };
      
      // 这里可以发送错误报告到服务器
      Logger.debug('Error report', errorReport);
      
      // 实际实现中可以调用API
      // await axios.post('/api/error-report', errorReport);
      
    } catch (reportError) {
      Logger.error('Failed to report error', reportError);
    }
  };

  return {
    // 状态
    errorState,
    ERROR_TYPES,
    
    // 方法
    handleError,
    manualRetry,
    clearError,
    resetRetryCount,
    getErrorInfo,
    reportError
  };
}

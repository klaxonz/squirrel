import { ref } from 'vue';

/**
 * 图片加载失败处理 composable
 * @param {string} defaultImage - 默认图片路径
 * @returns {Object} { failedImages, handleImageError, hasError, reset }
 */
export function useImageFallback(defaultImage = '/squirrel-icon.svg') {
  const failedImages = ref(new Set());
  
  const handleImageError = (event, identifier) => {
    if (identifier !== undefined && identifier !== null) {
      failedImages.value.add(identifier);
    }
    if (event?.target) {
      event.target.src = defaultImage;
    }
  };

  const getImageSrc = (src, identifier) => {
    if (identifier !== undefined && identifier !== null && failedImages.value.has(identifier)) {
      return defaultImage;
    }

    if (typeof src !== 'string') {
      return src ? src : defaultImage;
    }

    const trimmed = src.trim();
    return trimmed ? trimmed : defaultImage;
  };
  
  const hasError = (identifier) => {
    return failedImages.value.has(identifier);
  };
  
  const reset = () => {
    failedImages.value.clear();
  };
  
  return {
    failedImages,
    handleImageError,
    getImageSrc,
    hasError,
    reset
  };
}


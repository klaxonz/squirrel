import { ref } from 'vue';

/**
 * 图片加载失败处理 composable
 * @param {string} defaultImage - 默认图片路径
 * @returns {Object} { failedImages, handleImageError, hasError, reset }
 */
export function useImageFallback(defaultImage = '/squirrel-icon.svg') {
  const failedImages = ref(new Set());
  
  const handleImageError = (event, identifier) => {
    if (identifier) {
      failedImages.value.add(identifier);
    }
    if (event?.target) {
      event.target.src = defaultImage;
    }
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
    hasError,
    reset
  };
}


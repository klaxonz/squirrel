export const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  
  if (isNaN(date.getTime())) return '未知日期';
  
  const now = new Date();
  const hasTimeComponent = dateString.length > 10;

  // 获取当前日期和目标日期的年、月、日
  const todayYear = now.getFullYear();
  const todayMonth = now.getMonth();
  const todayDay = now.getDate();

  const dateYear = date.getFullYear();
  const dateMonth = date.getMonth();
  const dateDay = date.getDate();

  const diffTime = Math.abs(now - date);
  const diffDays = diffTime / (1000 * 60 * 60 * 24);
  const diffHours = diffTime / (1000 * 60 * 60);
  const diffMinutes = diffTime / (1000 * 60);

  // 比较日期
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay) {
    if (!hasTimeComponent) {
      return '今天';
    }
    if (diffMinutes < 60) {
      if (diffMinutes < 1) {
        return '刚刚';
      }
      return `${Math.floor(diffMinutes)}分钟前`;
    }
    if (diffHours < 24) {
      return `${Math.floor(diffHours)}小时前`;
    }
    return '今天';
  }

  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay - 1) {
    return '昨天';
  }
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay + 1) {
    return '明天';
  }
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay > todayDay) {
    return `${dateDay - todayDay}天后`;
  }

  // Only process minute/hour level differences if we have time component
  if (hasTimeComponent && diffDays < 1) {
    if (diffHours < 24) {
      if (diffMinutes < 60) {
        return `${Math.floor(diffMinutes)}分钟前`;
      } else {
        return `${Math.floor(diffHours)}小时前`;
      }
    }
  }

  if (diffDays <= 7) {
    if (date > now) {
      return `${Math.floor(diffDays)}天后`;
    } else {
      return `${Math.floor(diffDays)}天前`;
    }
  }
  if (diffDays <= 30) {
    if (date > now) {
      return `${Math.floor(diffDays / 7)}周后`;
    } else {
      return `${Math.floor(diffDays / 7)}周前`;
    }
  }
  if (diffDays <= 365) {
    if (date > now) {
      return `${Math.floor(diffDays / 30)}个月后`;
    } else {
      return `${Math.floor(diffDays / 30)}个月前`;
    }
  }
  if (date > now) {
    return `${Math.floor(diffDays / 365)}年后`;
  } else {
    return `${Math.floor(diffDays / 365)}年前`;
  }
};

// 如果需要其他日期格式化方法，也可以在这里添加
export const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return `${hours ? hours + ':' : ''}${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}; 

export const formatLastUpdate = (date) => {
  if (!date) return '未知';
  const updateDate = new Date(date);
  const now = new Date();
  const diffTime = Math.abs(now - updateDate);
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return '今天更新';
  if (diffDays === 1) return '昨天更新';
  if (diffDays < 7) return `${diffDays}天前更新`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前更新`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}个月前更新`;
  return `${Math.floor(diffDays / 365)}年前更新`;
};
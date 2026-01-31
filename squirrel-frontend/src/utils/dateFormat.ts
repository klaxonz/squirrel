type DateLike = string | number | Date

export const formatDate = (dateString: DateLike | null | undefined): string => {
  if (!dateString) return '未知日期'

  const raw = typeof dateString === 'string' ? dateString : String(dateString)
  const hasTimeComponent = raw.length > 10
  const date = new Date(dateString as any)

  if (Number.isNaN(date.getTime())) return '未知日期'

  const now = new Date()

  if (!hasTimeComponent) {
    const todayYear = now.getFullYear()
    const todayMonth = now.getMonth()
    const todayDay = now.getDate()

    const dateYear = date.getFullYear()
    const dateMonth = date.getMonth()
    const dateDay = date.getDate()

    if (dateYear === todayYear && dateMonth === todayMonth) {
      if (dateDay === todayDay) {
        return '今天'
      }
      if (dateDay === todayDay - 1) {
        return '昨天'
      }
      if (dateDay === todayDay + 1) {
        return '明天'
      }
      if (dateDay > todayDay) {
        return `${dateDay - todayDay}天后`
      }
    }

    const diffTime = Math.abs(now.getTime() - date.getTime())
    const diffDays = diffTime / (1000 * 60 * 60 * 24)

    if (diffDays <= 7) {
      if (date > now) {
        return `${Math.floor(diffDays)}天后`
      } else {
        return `${Math.floor(diffDays)}天前`
      }
    }
    if (diffDays <= 30) {
      if (date > now) {
        return `${Math.floor(diffDays / 7)}周后`
      } else {
        return `${Math.floor(diffDays / 7)}周前`
      }
    }
    if (diffDays <= 365) {
      if (date > now) {
        return `${Math.floor(diffDays / 30)}个月后`
      } else {
        return `${Math.floor(diffDays / 30)}个月前`
      }
    }
    if (date > now) {
      return `${Math.floor(diffDays / 365)}年后`
    } else {
      return `${Math.floor(diffDays / 365)}年前`
    }
  }

  const diffTime = Math.abs(now.getTime() - date.getTime())
  const diffDays = diffTime / (1000 * 60 * 60 * 24)
  const diffHours = diffTime / (1000 * 60 * 60)
  const diffMinutes = diffTime / (1000 * 60)

  if (diffDays < 1) {
    if (diffMinutes < 1) {
      return '刚刚'
    }
    if (diffMinutes < 60) {
      return `${Math.floor(diffMinutes)}分钟前`
    }
    if (diffHours < 24) {
      return `${Math.floor(diffHours)}小时前`
    }
  }

  const datePart = raw.includes('T') ? raw.split('T')[0] : raw.split(' ')[0]

  if (datePart === raw || datePart.length > 10) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  }

  return formatDate(datePart)
}

export const formatDuration = (seconds: number | null | undefined) => {
  if (!seconds) return '未知'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60
  return `${hours ? hours + ':' : ''}${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
}

export const formatTime = (seconds: number) => {
  const date = new Date(0)
  date.setSeconds(seconds)
  return date.toISOString().slice(11, 19).replace(/^00:/, '')
}

export const formatLastUpdate = (date: DateLike | null | undefined) => {
  if (!date) return '未知'
  const updateDate = new Date(date as any)
  const now = new Date()
  const diffTime = Math.abs(now.getTime() - updateDate.getTime())
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return '今天更新'
  if (diffDays === 1) return '昨天更新'
  if (diffDays < 7) return `${diffDays}天前更新`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前更新`
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}个月前更新`
  return `${Math.floor(diffDays / 365)}年前更新`
}

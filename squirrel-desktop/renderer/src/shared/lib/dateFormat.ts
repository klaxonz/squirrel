type DateLike = string | number | Date

const trimDecimal = (value: string) => {
  return value.replace(/\.0$/, '').replace(/(\.\d*[1-9])0+$/, '$1')
}

/** Calendar-style absolute date (local timezone of the parsed Date). */
const formatAbsoluteDate = (date: Date): string => {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

/**
 * Relative / calendar copy for feed timestamps.
 *
 * Past and near-future stay relative (Fluent-style scannable list). Far-future
 * or garbage schedule dates never become “N年后” — those render as absolute
 * YYYY-MM-DD. Near future (≤30d) still uses 天后/周后/月后.
 */
export const formatDate = (dateString: DateLike | null | undefined): string => {
  if (!dateString) return '未知日期'

  const raw = typeof dateString === 'string' ? dateString : String(dateString)
  const hasTimeComponent = raw.length > 10
  const date = new Date(dateString)

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

    const signedMs = date.getTime() - now.getTime()
    const isFuture = signedMs > 0
    const diffDays = Math.abs(signedMs) / (1000 * 60 * 60 * 24)

    // Far-future / bad feed dates → absolute, never “N年后”.
    if (isFuture && diffDays > 30) {
      return formatAbsoluteDate(date)
    }

    if (diffDays <= 7) {
      if (isFuture) {
        return `${Math.floor(diffDays)}天后`
      }
      return `${Math.floor(diffDays)}天前`
    }
    if (diffDays <= 30) {
      if (isFuture) {
        return `${Math.floor(diffDays / 7)}周后`
      }
      return `${Math.floor(diffDays / 7)}周前`
    }
    if (diffDays <= 365) {
      return `${Math.floor(diffDays / 30)}个月前`
    }
    return `${Math.floor(diffDays / 365)}年前`
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
    return formatAbsoluteDate(date)
  }

  return formatDate(datePart)
}

export const formatDuration = (seconds: number | null | undefined) => {
  if (!seconds) return '未知'
  const total = Math.floor(Number(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remainingSeconds = total % 60
  return `${hours ? hours + ':' : ''}${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
}

export const formatDurationMs = (durationMs: number | null | undefined, fallback = '—') => {
  if (durationMs == null || Number.isNaN(Number(durationMs))) {
    return fallback
  }

  const raw = Number(durationMs)
  if (raw === 0) {
    return fallback
  }
  const sign = raw < 0 ? '-' : ''
  const absolute = Math.abs(raw)

  if (absolute < 1000) {
    return `${sign}${Math.round(absolute)}ms`
  }

  if (absolute < 60_000) {
    const seconds = absolute / 1000
    const display = seconds < 10 ? trimDecimal(seconds.toFixed(1)) : String(Math.round(seconds))
    return `${sign}${display}秒`
  }

  if (absolute < 3_600_000) {
    const minutes = Math.floor(absolute / 60_000)
    const seconds = Math.round((absolute % 60_000) / 1000)
    if (seconds >= 60) {
      return `${sign}${minutes + 1}分钟`
    }
    return seconds > 0 ? `${sign}${minutes}分${seconds}秒` : `${sign}${minutes}分钟`
  }

  if (absolute < 86_400_000) {
    const hours = Math.floor(absolute / 3_600_000)
    const minutes = Math.floor((absolute % 3_600_000) / 60_000)
    return minutes > 0 ? `${sign}${hours}小时${minutes}分` : `${sign}${hours}小时`
  }

  const days = Math.floor(absolute / 86_400_000)
  const hours = Math.floor((absolute % 86_400_000) / 3_600_000)
  return hours > 0 ? `${sign}${days}天${hours}小时` : `${sign}${days}天`
}

export const formatTime = (seconds: number) => {
  const date = new Date(0)
  date.setSeconds(seconds)
  return date.toISOString().slice(11, 19).replace(/^00:/, '')
}

/**
 * Compact Chinese count formatting (亿/万). Anything ≥ 100M collapses to "x.x亿",
 * ≥ 10K to "x.x万", otherwise the raw number. Trailing ".0" is trimmed so we never
 * render "1.0万". The single source of truth for play counts, fan counts, etc.
 */
export const formatCount = (count: number | null | undefined): string => {
  if (count == null || Number.isNaN(Number(count))) return '0'
  const n = Number(count)
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1).replace(/\.0$/, '')}亿`
  if (n >= 10_000) return `${(n / 10_000).toFixed(1).replace(/\.0$/, '')}万`
  return String(n)
}

/**
 * 国际化 Composable
 */

import { ref, computed, type Ref } from 'vue'
import type { LocaleCode, LocaleMessages, LocaleConfig } from './types'
import zhCN from './zh-CN'
import enUS from './en-US'
import jaJP from './ja-JP'
import { Logger } from '@/utils/logger'

// 内置语言包
const builtInLocales: Record<string, LocaleConfig> = {
  'zh-CN': zhCN,
  'en-US': enUS,
  'ja-JP': jaJP
}

// 全局语言状态
const globalLocale = ref<LocaleCode>('zh-CN')
const customLocales = ref<Record<string, LocaleConfig>>({})

export interface UseI18nOptions {
  locale?: LocaleCode
  fallbackLocale?: LocaleCode
}

export interface UseI18nReturn {
  locale: Ref<LocaleCode>
  availableLocales: Ref<LocaleCode[]>
  messages: Ref<LocaleMessages>
  t: (key: keyof LocaleMessages, params?: Record<string, string | number>) => string
  setLocale: (locale: LocaleCode) => void
  addLocale: (config: LocaleConfig) => void
  getLocaleName: (code: LocaleCode) => string
}

/**
 * 检测浏览器语言
 */
function detectBrowserLocale(): LocaleCode {
  if (typeof navigator === 'undefined') return 'zh-CN'
  
  const browserLang = navigator.language || (navigator as any).userLanguage
  
  // 精确匹配
  if (builtInLocales[browserLang]) {
    return browserLang as LocaleCode
  }
  
  // 语言代码匹配 (如 zh -> zh-CN)
  const langCode = browserLang.split('-')[0]
  const matched = Object.keys(builtInLocales).find(k => k.startsWith(langCode))
  
  return (matched as LocaleCode) || 'en-US'
}

/**
 * 国际化 Composable
 */
export function useI18n(options: UseI18nOptions = {}): UseI18nReturn {
  const { 
    locale: initialLocale,
    fallbackLocale = 'en-US'
  } = options

  // 初始化语言
  if (initialLocale) {
    globalLocale.value = initialLocale
  } else if (globalLocale.value === 'zh-CN') {
    // 首次使用时检测浏览器语言
    const saved = typeof localStorage !== 'undefined' 
      ? localStorage.getItem('sp-locale') as LocaleCode | null
      : null
    globalLocale.value = saved || detectBrowserLocale()
  }

  // 可用语言列表
  const availableLocales = computed(() => {
    return [...Object.keys(builtInLocales), ...Object.keys(customLocales.value)] as LocaleCode[]
  })

  // 当前语言消息
  const messages = computed(() => {
    const locale = globalLocale.value
    const config = customLocales.value[locale] || builtInLocales[locale] || builtInLocales[fallbackLocale]
    return config?.messages || builtInLocales['en-US'].messages
  })

  /**
   * 翻译函数
   */
  const t = (key: keyof LocaleMessages, params?: Record<string, string | number>): string => {
    let text = messages.value[key] || key
    
    // 替换参数
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      })
    }
    
    return text
  }

  /**
   * 设置语言
   */
  const setLocale = (locale: LocaleCode): void => {
    if (!availableLocales.value.includes(locale)) {
      Logger.warn(`[i18n] Locale "${locale}" not available`)
      return
    }
    
    globalLocale.value = locale
    
    // 持久化
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('sp-locale', locale)
    }
    
    // 更新 HTML lang 属性
    if (typeof document !== 'undefined') {
      document.documentElement.lang = locale
    }
  }

  /**
   * 添加自定义语言包
   */
  const addLocale = (config: LocaleConfig): void => {
    customLocales.value[config.code] = config
  }

  /**
   * 获取语言名称
   */
  const getLocaleName = (code: LocaleCode): string => {
    const config = customLocales.value[code] || builtInLocales[code]
    return config?.name || code
  }

  return {
    locale: globalLocale,
    availableLocales,
    messages,
    t,
    setLocale,
    addLocale,
    getLocaleName
  }
}

export default useI18n

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router'
import { queryClient } from '@/shared/lib/queryClient'
import { useThemeStore } from '@/shared/stores/theme'
import { Logger } from '@/shared/lib/logger'
import { hoverFill } from '@/shared/directives/hoverFill'
// UI copy uses the platform system font stack (see --font-sans in index.css).
// Outfit (geometric, Gilroy-adjacent) carries display headings and numerals;
// JetBrains Mono is reserved for code/timestamps. Noto Sans SC is the Linux
// CJK fallback; Windows/macOS resolve to YaHei/PingFang first.
import '@fontsource-variable/outfit/wght.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/600.css'
// Noto Sans SC Variable (思源黑体, Google) — variable weight 100-900, ~4.3 MiB
// woff2 split into 101 unicode-range slices so only needed CJK chunks load.
import '@fontsource-variable/noto-sans-sc/wght.css'
import '@/shared/styles/index.css'
import '@/shared/styles/components.css'
import '@/shared/styles/layout.css'
import '@/shared/styles/themes/dark.css'
import '@/features/auth/styles/auth-entry.css'

const bootstrap = async () => {
  // Prevent browser from restoring scroll position on page load,
  // which causes the subtle auto-scroll issue.
  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual'
  }

  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  app.use(VueQueryPlugin, { queryClient })
  app.directive('hover-fill', hoverFill)

  // ponytail: global last-resort sinks. Per-request API errors surface as
  // thrown ApiError (caught by vue-query's MutationCache → toast, or by each
  // view's try/catch); the 401 → logout side-effect lives in the axios
  // interceptor. These two only catch genuinely unhandled throws.
  app.config.errorHandler = (error, instance, info) => {
    Logger.error('Uncaught Vue error', error, { info, component: instance?.$?.type?.name })
  }
  window.addEventListener('unhandledrejection', (event) => {
    Logger.error('Unhandled promise rejection', event.reason)
  })

  const themeStore = useThemeStore()
  themeStore.init()

  await router.isReady()
  app.mount('#app')
}

void bootstrap()

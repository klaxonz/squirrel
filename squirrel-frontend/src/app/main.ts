import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router'
import { queryClient } from '@/shared/lib/queryClient'
import { useThemeStore } from '@/shared/stores/theme'
import { Logger } from '@/shared/lib/logger'

import '@/shared/styles/index.css'
import '@/shared/styles/layout.css'
import '@/shared/styles/themes/dark.css'

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

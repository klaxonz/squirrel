import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import { Logger } from './utils/logger'

import './styles/index.css'
import './styles/layout.css'
import './styles/themes/dark.css'

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

  // ponytail: global last-resort sinks. Per-request API errors are handled by
  // the axios interceptor (401 -> logout) and the { data, error } return shape
  // from handleRequest; these two only catch genuinely unhandled throws.
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

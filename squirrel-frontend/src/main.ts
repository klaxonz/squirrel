import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import { vueErrorHandler, unhandledRejectionHandler } from './utils/errorHandler'

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

  app.config.errorHandler = vueErrorHandler
  window.addEventListener('unhandledrejection', unhandledRejectionHandler)

  const themeStore = useThemeStore()
  themeStore.init()

  await router.isReady()
  app.mount('#app')
}

void bootstrap()

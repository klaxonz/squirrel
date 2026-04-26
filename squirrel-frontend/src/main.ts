import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { vueErrorHandler, unhandledRejectionHandler } from './utils/errorHandler'
import { initializeAppTheme } from './composables/useAppTheme'

import './styles/index.css'
import './styles/layout.css'
import './styles/themes/dark.css'
import '@fortawesome/fontawesome-free/css/all.min.css'

const isDesktopShell = typeof window !== 'undefined' && window.desktopApp?.isDesktop === true

if (!isDesktopShell) {
  document.addEventListener('contextmenu', (event) => {
    event.preventDefault()
  })
}

initializeAppTheme()

const bootstrap = async () => {
  const app = createApp(App)

  app.config.errorHandler = vueErrorHandler

  window.addEventListener('unhandledrejection', unhandledRejectionHandler)

  const pinia = createPinia()

  app.use(pinia)
  app.use(router)

  await router.isReady()
  app.mount('#app')
}

void bootstrap()

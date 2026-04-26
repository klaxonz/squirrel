import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import { vueErrorHandler, unhandledRejectionHandler } from './utils/errorHandler'

import './styles/index.css'
import './styles/layout.css'
import './styles/themes/dark.css'
import '@fortawesome/fontawesome-free/css/all.min.css'

const bootstrap = async () => {
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

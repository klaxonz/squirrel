import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { vueErrorHandler, unhandledRejectionHandler } from './utils/errorHandler'
import { initializeAppTheme } from './composables/useAppTheme'

import './styles/index.css'
import '@fortawesome/fontawesome-free/css/all.min.css'
import './utils/iconify'

document.addEventListener('contextmenu', (event) => {
  event.preventDefault()
})

initializeAppTheme()

const app = createApp(App)

app.config.errorHandler = vueErrorHandler

window.addEventListener('unhandledrejection', unhandledRejectionHandler)

const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')

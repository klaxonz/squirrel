import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { vueErrorHandler, unhandledRejectionHandler } from './utils/errorHandler'

import './styles/index.css'
import '@fortawesome/fontawesome-free/css/all.min.css'
import './utils/iconify'

// 阻止默认的右键菜单
document.addEventListener('contextmenu', (event) => {
  event.preventDefault()
})

// 设置全局错误处理器
const app = createApp(App)

// Vue 错误处理
app.config.errorHandler = vueErrorHandler

// 未处理的 Promise 拒绝
window.addEventListener('unhandledrejection', unhandledRejectionHandler)

const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')

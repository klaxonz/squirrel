import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

import Toast from 'vue-toastification';
import 'vue-toastification/dist/index.css';
import './styles/index.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import './styles/toast.css'
import './utils/iconify'

// 阻止默认的右键菜单
document.addEventListener('contextmenu', (event) => {
  event.preventDefault();
});

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Toast, {
    maxToasts: 1,
    toastClassName: "youtube-toast",
    containerClassName: "youtube-toast-container"
})
app.mount('#app')

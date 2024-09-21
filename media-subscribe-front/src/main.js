import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import Toast from 'vue-toastification';
import 'vue-toastification/dist/index.css';
import './index.css';

const app = createApp(App)
app.use(router)
app.use(Toast, {
    maxToasts: 1,
    toastClassName: "custom-toast",
    containerClassName: "custom-toast-container",
})
app.mount('#app')
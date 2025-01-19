import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import Toast from 'vue-toastification';
import 'vue-toastification/dist/index.css';
import './index.css';
import Player from 'xgplayer';
import 'xgplayer/dist/index.min.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import VueVirtualScroller from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import './styles/toast.css'

// 阻止默认的右键菜单
document.addEventListener('contextmenu', (event) => {
  event.preventDefault();
});

const app = createApp(App)
app.use(router)
app.use(Toast, {
    maxToasts: 1,
    toastClassName: "youtube-toast",
    containerClassName: "youtube-toast-container"
})
app.use(VueVirtualScroller)
app.config.globalProperties.$Player = Player;
app.mount('#app')

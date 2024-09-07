import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import InfiniteLoading from "v3-infinite-loading";
import "v3-infinite-loading/lib/style.css";
import Toast from 'vue-toastification';
import 'vue-toastification/dist/index.css';

const app = createApp(App)
app.use(router)
app.use(Toast)
app.component('infinite-loading', InfiniteLoading);
app.mount('#app')
import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import router from './router'
import store from './store'
import App from './App.vue'
import axios from 'axios'
import 'ant-design-vue/dist/reset.css'

// 配置axios - 统一使用/api作为baseURL
// 组件中直接使用相对路径（如 /results），不需要包含/api前缀
axios.defaults.baseURL = process.env.NODE_ENV === 'production'
  ? '/api'  // 生产环境使用相对路径，由Flask提供API
  : 'http://localhost:5678/api'  // 开发环境使用Flask服务器

const app = createApp(App)

app.use(Antd)
app.use(router)
app.use(store)

app.mount('#app')

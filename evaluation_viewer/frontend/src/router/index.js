import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Detail from '../views/Detail.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: {
      title: '评测结果列表'
    }
  },
  {
    path: '/detail/:alarmId',
    name: 'Detail',
    component: Detail,
    meta: {
      title: '评测结果详情'
    },
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：设置页面标题
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 评测结果展示系统`
  }
  next()
})

export default router

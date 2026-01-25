import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '工作台', icon: 'Odometer' }
      },
      {
        path: 'inventory',
        name: 'Inventory',
        component: () => import('@/views/inventory/index.vue'),
        meta: { title: '库存管理', icon: 'Box' }
      },
      {
        path: 'procurement',
        name: 'Procurement',
        component: () => import('@/views/procurement/index.vue'),
        meta: { title: '采购分析', icon: 'DataAnalysis' }
      },
      {
        path: 'system/users',
        name: 'Users',
        component: () => import('@/views/system/users.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'system/roles',
        name: 'Roles',
        component: () => import('@/views/system/roles.vue'),
        meta: { title: '角色管理', icon: 'UserFilled' }
      },
      {
        path: 'system/menus',
        name: 'Menus',
        component: () => import('@/views/system/menus.vue'),
        meta: { title: '菜单管理', icon: 'Menu' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 智能采购管理系统` : '智能采购管理系统'
  
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth === false) {
    if (userStore.isLoggedIn && to.path === '/login') {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    if (userStore.isLoggedIn) {
      next()
    } else {
      next('/login')
    }
  }
})

export default router

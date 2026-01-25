import { defineStore } from 'pinia'
import { login as loginApi, getUserInfo, getUserMenus } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || '{}'),
    menus: JSON.parse(localStorage.getItem('menus') || '[]')
  }),
  
  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo.username || '',
    nickname: (state) => state.userInfo.nickname || state.userInfo.username || '',
    roles: (state) => state.userInfo.roles || [],
    permissions: (state) => state.userInfo.permissions || [],
    isAdmin: (state) => state.userInfo.roles?.includes('admin') || false
  },
  
  actions: {
    async login(username, password) {
      try {
        const res = await loginApi({ username, password })
        this.token = res.access_token
        this.userInfo = res.user_info
        localStorage.setItem('token', this.token)
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        
        // Get menus
        await this.fetchMenus()
        
        return res
      } catch (error) {
        throw error
      }
    },
    
    async fetchMenus() {
      try {
        const menus = await getUserMenus()
        this.menus = menus
        localStorage.setItem('menus', JSON.stringify(menus))
        return menus
      } catch (error) {
        console.error('Failed to fetch menus:', error)
        return []
      }
    },
    
    async fetchUserInfo() {
      try {
        const userInfo = await getUserInfo()
        this.userInfo = userInfo
        localStorage.setItem('userInfo', JSON.stringify(userInfo))
        return userInfo
      } catch (error) {
        throw error
      }
    },
    
    logout() {
      this.token = ''
      this.userInfo = {}
      this.menus = []
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      localStorage.removeItem('menus')
    },
    
    hasPermission(permission) {
      if (this.isAdmin) return true
      return this.permissions.includes(permission)
    }
  }
})

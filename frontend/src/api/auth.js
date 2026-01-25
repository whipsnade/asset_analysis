import request from '@/utils/request'

export function login(data) {
  return request.post('/auth/login', data)
}

export function getUserInfo() {
  return request.get('/auth/info')
}

export function getUserMenus() {
  return request.get('/auth/menus')
}

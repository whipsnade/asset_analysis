import request from '@/utils/request'

// Users
export function getUserList() {
  return request.get('/system/users')
}

export function createUser(data) {
  return request.post('/system/users', data)
}

export function updateUser(id, data) {
  return request.put(`/system/users/${id}`, data)
}

export function deleteUser(id) {
  return request.delete(`/system/users/${id}`)
}

// Roles
export function getRoleList() {
  return request.get('/system/roles')
}

export function createRole(data) {
  return request.post('/system/roles', data)
}

export function updateRole(id, data) {
  return request.put(`/system/roles/${id}`, data)
}

export function deleteRole(id) {
  return request.delete(`/system/roles/${id}`)
}

export function getRoleMenus(id) {
  return request.get(`/system/roles/${id}/menus`)
}

export function assignRoleMenus(id, menuIds) {
  return request.put(`/system/roles/${id}/menus`, menuIds)
}

// Menus
export function getMenuList() {
  return request.get('/system/menus')
}

export function createMenu(data) {
  return request.post('/system/menus', data)
}

export function deleteMenu(id) {
  return request.delete(`/system/menus/${id}`)
}

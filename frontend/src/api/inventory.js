import request from '@/utils/request'

export function getInventoryList(params) {
  return request.get('/inventory', { params })
}

export function getInventory(id) {
  return request.get(`/inventory/${id}`)
}

export function createInventory(data) {
  return request.post('/inventory', data)
}

export function updateInventory(id, data) {
  return request.put(`/inventory/${id}`, data)
}

export function deleteInventory(id) {
  return request.delete(`/inventory/${id}`)
}

export function importInventory(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/inventory/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function getCategories() {
  return request.get('/inventory/categories')
}

import request from '@/utils/request'

export function analyzeText(content, sessionId) {
  return request.post('/procurement/analyze-text', { content }, {
    headers: sessionId ? { 'X-Session-Id': sessionId } : {},
    timeout: 120000
  })
}

export function analyzeFile(file, sessionId) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/procurement/analyze-file', formData, {
    headers: { 
      'Content-Type': 'multipart/form-data',
      ...(sessionId ? { 'X-Session-Id': sessionId } : {})
    },
    timeout: 120000  // 2 minutes for AI processing
  })
}

export function analyzeFiles(files, sessionId) {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })
  return request.post('/procurement/analyze-files', formData, {
    headers: { 
      'Content-Type': 'multipart/form-data',
      ...(sessionId ? { 'X-Session-Id': sessionId } : {})
    },
    timeout: 300000  // 5 minutes for multiple files
  })
}

export function getTaskList(params) {
  return request.get('/procurement/tasks', { params })
}

export function getTask(id) {
  return request.get(`/procurement/tasks/${id}`)
}

export function exportResult(data) {
  return request.post('/procurement/export', data, {
    responseType: 'blob'
  })
}

export function getLogStreamUrl(sessionId) {
  return `/api/v1/procurement/logs/${sessionId}`
}

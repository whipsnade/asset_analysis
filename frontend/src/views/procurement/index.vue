<template>
  <div class="procurement-page">
    <el-row :gutter="20">
      <!-- Input Section -->
      <el-col :span="10">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>采购需求输入</span>
              <el-radio-group v-model="inputType" size="small">
                <el-radio-button value="text">文本输入</el-radio-button>
                <el-radio-button value="file">文件上传</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <div v-if="inputType === 'text'" class="text-input">
            <el-input
              v-model="textContent"
              type="textarea"
              :rows="10"
              placeholder="请粘贴客户的采购需求内容，例如：&#10;1. 32寸叫号屏 2台&#10;2. POE交换机16口 1个&#10;3. 监控摄像头200万像素 10个"
            />
            <el-button
              type="primary"
              :loading="analyzing"
              :disabled="!textContent.trim()"
              style="margin-top: 15px; width: 100%;"
              @click="analyzeTextContent"
            >
              <el-icon><DataAnalysis /></el-icon>
              开始智能分析
            </el-button>
          </div>

          <div v-else class="file-input">
            <el-upload
              ref="uploadRef"
              drag
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :on-remove="() => selectedFile = null"
              accept=".xlsx,.xls"
            >
              <el-icon size="48" color="#409EFF"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                拖拽Excel文件到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .xlsx, .xls 格式的采购需求表
                </div>
              </template>
            </el-upload>
            <el-button
              type="primary"
              :loading="analyzing"
              :disabled="!selectedFile"
              style="margin-top: 15px; width: 100%;"
              @click="analyzeFileContent"
            >
              <el-icon><DataAnalysis /></el-icon>
              开始智能分析
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- Result Section -->
      <el-col :span="14">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>匹配结果</span>
              <div class="header-actions">
                <el-tag v-if="analyzeResult.status" :type="statusType" style="margin-right: 10px;">
                  {{ analyzeResult.message }}
                </el-tag>
                <el-button 
                  v-if="analyzeResult.details?.length" 
                  type="success" 
                  size="small"
                  @click="showExportDialog"
                >
                  <el-icon><Download /></el-icon>
                  导出Excel
                </el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!analyzeResult.details?.length" description="暂无分析结果，请输入采购需求后点击分析" />

          <div v-else class="result-list">
            <div v-for="(item, index) in analyzeResult.details" :key="item.id" class="result-item">
              <div class="result-header">
                <span class="result-index">{{ index + 1 }}</span>
                <el-tag :type="getConfidenceType(item.confidence_score)" size="small">
                  匹配度: {{ Math.round((item.confidence_score || 0) * 100) }}%
                </el-tag>
              </div>
              
              <el-row :gutter="15" class="result-content">
                <el-col :span="12">
                  <div class="result-section">
                    <div class="section-title">客户需求</div>
                    <div class="section-body">
                      <p><strong>产品名称:</strong> {{ item.parsed_name || '-' }}</p>
                      <p><strong>规格型号:</strong> {{ item.parsed_spec || '-' }}</p>
                      <p><strong>采购数量:</strong> {{ item.parsed_quantity || '-' }}</p>
                    </div>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="result-section matched">
                    <div class="section-title">匹配库存</div>
                    <div class="section-body" v-if="item.matched_inventory">
                      <p><strong>产品名称:</strong> {{ item.matched_inventory.product_name }}</p>
                      <p><strong>规格型号:</strong> {{ item.matched_inventory.spec || '-' }}</p>
                      <p><strong>库存数量:</strong> {{ item.matched_inventory.quantity }} {{ item.matched_inventory.unit }}</p>
                      <p><strong>销售单价:</strong> {{ item.matched_inventory.sale_price || '-' }}</p>
                      <p><strong>供应商:</strong> {{ item.matched_inventory.supplier || '-' }}</p>
                    </div>
                    <div class="section-body no-match" v-else>
                      <p>未找到匹配的库存项</p>
                    </div>
                  </div>
                </el-col>
              </el-row>
              
              <div class="match-reason" v-if="item.match_reason">
                <el-icon><InfoFilled /></el-icon>
                {{ item.match_reason }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Export Dialog -->
    <el-dialog v-model="exportDialogVisible" title="导出采购清单" width="600px">
      <el-form :model="exportForm" label-width="120px">
        <el-form-item label="客户名称缩写">
          <el-input v-model="exportForm.customer_abbr" placeholder="请输入客户名称缩写" />
        </el-form-item>
        <el-form-item label="项目/门店名称">
          <el-input v-model="exportForm.project_name" placeholder="请输入项目或门店名称" />
        </el-form-item>
        <el-form-item label="我方开票抬头">
          <el-input v-model="exportForm.invoice_title" placeholder="请输入我方开票抬头" />
        </el-form-item>
        <el-form-item label="需求发起人">
          <el-input v-model="exportForm.requester" placeholder="请输入需求发起人" />
        </el-form-item>
        <el-form-item label="采购应下单日期">
          <el-date-picker
            v-model="exportForm.order_date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="收货地址">
          <el-input v-model="exportForm.delivery_address" type="textarea" :rows="2" placeholder="请输入收货地址" />
        </el-form-item>
        <el-form-item label="最低匹配度">
          <div style="display: flex; align-items: center; width: 100%;">
            <el-slider 
              v-model="exportForm.min_confidence" 
              :min="0" 
              :max="100" 
              :step="5"
              :format-tooltip="(val) => val + '%'"
              style="flex: 1; margin-right: 15px;"
            />
            <span style="width: 50px; text-align: right;">{{ exportForm.min_confidence }}%</span>
          </div>
          <div class="export-filter-info">
            符合条件: {{ filteredExportCount }} / {{ analyzeResult.details?.length || 0 }} 条
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="handleExport">
          <el-icon><Download /></el-icon>
          确认导出
        </el-button>
      </template>
    </el-dialog>

    <!-- Progress Dialog -->
    <el-dialog 
      v-model="progressDialogVisible" 
      title="AI智能分析中" 
      width="650px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!analyzing"
    >
      <div class="progress-content">
        <div class="progress-status">
          <el-icon v-if="analyzing" class="is-loading" :size="20"><Loading /></el-icon>
          <el-icon v-else-if="analyzeResult.status === 'completed'" :size="20" color="#67c23a"><CircleCheck /></el-icon>
          <el-icon v-else :size="20" color="#f56c6c"><CircleClose /></el-icon>
          <span class="status-text">{{ progressStatusText }}</span>
        </div>
        
        <el-progress 
          :percentage="progressPercentage" 
          :status="progressStatus"
          :stroke-width="12"
          style="margin: 15px 0;"
        />
        
        <div class="progress-log-panel">
          <div class="progress-log-header">
            <span>DeepSeek API 调用日志</span>
            <span class="log-count">{{ logs.length }} 条</span>
          </div>
          <div class="progress-log-content" ref="logContainer">
            <div 
              v-for="(log, index) in logs" 
              :key="index" 
              class="log-line"
              :class="'log-' + log.level.toLowerCase()"
            >
              <span class="log-time">{{ log.time }}</span>
              <span class="log-level">[{{ log.level }}]</span>
              <span class="log-msg">{{ log.message }}</span>
            </div>
            <div v-if="analyzing && logs.length === 0" class="log-line log-info">
              <span class="log-msg">正在连接AI服务...</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="!analyzing" type="primary" @click="progressDialogVisible = false">
          确定
        </el-button>
        <el-button v-else disabled>
          <el-icon class="is-loading"><Loading /></el-icon>
          分析中...
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { analyzeText, analyzeFile, exportResult, getLogStreamUrl } from '@/api/procurement'

const inputType = ref('text')
const textContent = ref('')
const selectedFile = ref(null)
const analyzing = ref(false)
const uploadRef = ref(null)
const exportDialogVisible = ref(false)
const exporting = ref(false)
const progressDialogVisible = ref(false)
const logContainer = ref(null)
const logs = ref([])
const progressPercentage = ref(0)
let eventSource = null
let sessionId = null

const analyzeResult = reactive({
  task_id: null,
  status: '',
  message: '',
  details: []
})

const exportForm = reactive({
  customer_abbr: '',
  project_name: '',
  invoice_title: '',
  requester: '',
  order_date: '',
  delivery_address: '',
  min_confidence: 0
})

const filteredExportCount = computed(() => {
  if (!analyzeResult.details?.length) return 0
  const threshold = exportForm.min_confidence / 100
  return analyzeResult.details.filter(item => (item.confidence_score || 0) >= threshold).length
})

const statusType = computed(() => {
  if (analyzeResult.status === 'completed') return 'success'
  if (analyzeResult.status === 'failed') return 'danger'
  return 'info'
})

const progressStatus = computed(() => {
  if (analyzing.value) return ''
  if (analyzeResult.status === 'completed') return 'success'
  if (analyzeResult.status === 'failed') return 'exception'
  return ''
})

const progressStatusText = computed(() => {
  if (analyzing.value) return '正在使用 DeepSeek AI 分析采购需求...'
  if (analyzeResult.status === 'completed') return `分析完成，共匹配 ${analyzeResult.details?.length || 0} 条需求`
  if (analyzeResult.status === 'failed') return '分析失败，请重试'
  return '准备中...'
})

const getConfidenceType = (score) => {
  if (!score) return 'info'
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'danger'
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const generateSessionId = () => {
  return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

const startLogStream = () => {
  sessionId = generateSessionId()
  logs.value = []
  
  const url = getLogStreamUrl(sessionId)
  eventSource = new EventSource(url)
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'heartbeat') return
      
      logs.value.push(data)
      
      // Auto scroll to bottom
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
    } catch (e) {
      console.error('Failed to parse log:', e)
    }
  }
  
  eventSource.onerror = () => {
    // Connection closed, stop listening
    stopLogStream()
  }
}

const stopLogStream = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const clearLogs = () => {
  logs.value = []
}

const analyzeTextContent = async () => {
  if (!textContent.value.trim()) {
    ElMessage.warning('请输入采购需求内容')
    return
  }

  // Reset and show progress dialog
  logs.value = []
  progressPercentage.value = 10
  progressDialogVisible.value = true
  analyzing.value = true
  startLogStream()
  
  try {
    progressPercentage.value = 30
    const res = await analyzeText(textContent.value, sessionId)
    Object.assign(analyzeResult, res)
    progressPercentage.value = 100
    ElMessage.success('分析完成')
  } catch (error) {
    analyzeResult.status = 'failed'
    analyzeResult.message = '分析失败'
    analyzeResult.details = []
    progressPercentage.value = 100
  } finally {
    analyzing.value = false
    stopLogStream()
  }
}

const analyzeFileContent = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择要上传的文件')
    return
  }

  // Reset and show progress dialog
  logs.value = []
  progressPercentage.value = 10
  progressDialogVisible.value = true
  analyzing.value = true
  startLogStream()
  
  try {
    progressPercentage.value = 30
    const res = await analyzeFile(selectedFile.value, sessionId)
    Object.assign(analyzeResult, res)
    progressPercentage.value = 100
    ElMessage.success('分析完成')
  } catch (error) {
    analyzeResult.status = 'failed'
    analyzeResult.message = '分析失败'
    analyzeResult.details = []
    progressPercentage.value = 100
  } finally {
    analyzing.value = false
    stopLogStream()
  }
}

const showExportDialog = () => {
  exportDialogVisible.value = true
}

const handleExport = async () => {
  // Filter by confidence threshold
  const threshold = exportForm.min_confidence / 100
  const filteredDetails = analyzeResult.details.filter(
    item => (item.confidence_score || 0) >= threshold
  )
  
  if (filteredDetails.length === 0) {
    ElMessage.warning('没有符合匹配度条件的数据可导出')
    return
  }
  
  exporting.value = true
  try {
    const data = {
      ...exportForm,
      details: filteredDetails.map(item => ({
        parsed_name: item.parsed_name || '',
        parsed_spec: item.parsed_spec || '',
        parsed_quantity: item.parsed_quantity || '',
        matched_inventory: item.matched_inventory || null,
        remark: '',
        purchase_link: ''
      }))
    }
    
    const response = await exportResult(data)
    
    // Create download link
    const blob = new Blob([response], { 
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `采购清单_${new Date().toISOString().slice(0, 10)}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
    exportDialogVisible.value = false
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopLogStream()
})
</script>

<style scoped>
.procurement-page {
  height: calc(100vh - 140px);
}

.input-card,
.result-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.text-input,
.file-input {
  height: 100%;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-height: calc(100vh - 250px);
  overflow-y: auto;
}

.result-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 15px;
  background: #fafafa;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.result-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: #409EFF;
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
}

.result-section {
  background: #fff;
  border-radius: 6px;
  padding: 12px;
  border: 1px solid #ebeef5;
}

.result-section.matched {
  background: #f0f9eb;
  border-color: #e1f3d8;
}

.section-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: #606266;
  font-size: 13px;
}

.section-body p {
  margin: 5px 0;
  font-size: 13px;
  color: #606266;
}

.section-body.no-match {
  color: #909399;
  font-style: italic;
}

.match-reason {
  margin-top: 10px;
  padding: 8px 12px;
  background: #ecf5ff;
  border-radius: 4px;
  font-size: 12px;
  color: #409EFF;
  display: flex;
  align-items: center;
  gap: 5px;
}

/* Log Panel Styles */
.log-panel {
  margin-top: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.log-content {
  height: 150px;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 8px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 11px;
  line-height: 1.5;
}

.log-line {
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-time {
  color: #6a9955;
  margin-right: 8px;
}

.log-level {
  margin-right: 8px;
  font-weight: bold;
}

.log-msg {
  color: #d4d4d4;
}

.log-info .log-level {
  color: #4fc1ff;
}

.log-debug .log-level {
  color: #9cdcfe;
}

.log-debug .log-msg {
  color: #808080;
}

.log-warn .log-level {
  color: #dcdcaa;
}

.log-warn .log-msg {
  color: #dcdcaa;
}

.log-error .log-level {
  color: #f14c4c;
}

.log-error .log-msg {
  color: #f14c4c;
}

.export-filter-info {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

/* Progress Dialog Styles */
.progress-content {
  padding: 10px;
}

.progress-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  color: #303133;
}

.progress-status .status-text {
  font-weight: 500;
}

.progress-log-panel {
  margin-top: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.progress-log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.progress-log-header .log-count {
  font-size: 12px;
  color: #909399;
}

.progress-log-content {
  height: 200px;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 10px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
}
</style>

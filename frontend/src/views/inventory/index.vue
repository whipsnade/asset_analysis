<template>
  <div class="inventory-page">
    <!-- Search & Actions -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="产品名称/规格" clearable />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="searchForm.category" placeholder="选择分类" clearable style="width: 150px;">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      <div class="action-buttons">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新增
        </el-button>
        <el-upload
          ref="uploadRef"
          :show-file-list="false"
          :before-upload="handleImport"
          accept=".xlsx,.xls"
        >
          <el-button type="success">
            <el-icon><Upload /></el-icon> 导入Excel
          </el-button>
        </el-upload>
      </div>
    </el-card>

    <!-- Data Table -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="product_name" label="产品名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="category" label="设备分类" width="140" show-overflow-tooltip />
        <el-table-column prop="spec" label="型号规格" min-width="180" show-overflow-tooltip />
        <el-table-column prop="quantity" label="数量" width="80" align="center" />
        <el-table-column prop="unit" label="单位" width="60" align="center" />
        <el-table-column prop="sale_price" label="销售单价" width="100" align="right">
          <template #default="{ row }">
            {{ row.sale_price ? `¥${row.sale_price}` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="purchase_price" label="采购单价" width="100" align="right">
          <template #default="{ row }">
            {{ row.purchase_price ? `¥${row.purchase_price}` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="supplier" label="供应商" width="100" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="loadData"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>

    <!-- Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editForm.id ? '编辑库存' : '新增库存'"
      width="600px"
    >
      <el-form ref="formRef" :model="editForm" :rules="formRules" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="产品名称" prop="product_name">
              <el-input v-model="editForm.product_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备分类" prop="category">
              <el-input v-model="editForm.category" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商" prop="supplier">
              <el-input v-model="editForm.supplier" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="型号规格" prop="spec">
              <el-input v-model="editForm.spec" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数量" prop="quantity">
              <el-input-number v-model="editForm.quantity" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="editForm.unit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="销售单价" prop="sale_price">
              <el-input-number v-model="editForm.sale_price" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采购单价" prop="purchase_price">
              <el-input-number v-model="editForm.purchase_price" :min="0" :precision="2" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="合同备注" prop="contract_remark">
              <el-input v-model="editForm.contract_remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getInventoryList, getCategories, createInventory, 
  updateInventory, deleteInventory, importInventory 
} from '@/api/inventory'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const tableData = ref([])
const categories = ref([])
const formRef = ref(null)

const searchForm = reactive({
  keyword: '',
  category: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const editForm = reactive({
  id: null,
  product_name: '',
  category: '',
  spec: '',
  quantity: 0,
  unit: '',
  sale_price: 0,
  purchase_price: 0,
  supplier: '',
  contract_remark: ''
})

const formRules = {
  product_name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getInventoryList({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      category: searchForm.category || undefined
    })
    tableData.value = res.items
    pagination.total = res.total
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    categories.value = await getCategories()
  } catch (error) {
    console.error(error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const resetSearch = () => {
  searchForm.keyword = ''
  searchForm.category = ''
  handleSearch()
}

const resetForm = () => {
  Object.assign(editForm, {
    id: null,
    product_name: '',
    category: '',
    spec: '',
    quantity: 0,
    unit: '',
    sale_price: 0,
    purchase_price: 0,
    supplier: '',
    contract_remark: ''
  })
}

const handleAdd = () => {
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(editForm, {
    ...row,
    // 确保数字字段有正确的值，null/undefined 转为 0
    quantity: row.quantity ?? 0,
    sale_price: row.sale_price ?? 0,
    purchase_price: row.purchase_price ?? 0
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editForm.id) {
      await updateInventory(editForm.id, editForm)
      ElMessage.success('更新成功')
    } else {
      await createInventory(editForm)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
    loadCategories()
  } catch (error) {
    console.error(error)
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该记录吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteInventory(row.id)
      ElMessage.success('删除成功')
      loadData()
    } catch (error) {
      console.error(error)
    }
  }).catch(() => {})
}

const handleImport = async (file) => {
  try {
    const res = await importInventory(file)
    ElMessage.success(res.message || '导入成功')
    loadData()
    loadCategories()
  } catch (error) {
    console.error(error)
  }
  return false
}

onMounted(() => {
  loadData()
  loadCategories()
})
</script>

<style scoped>
.inventory-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-card :deep(.el-card__body) {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
}

.action-buttons {
  display: flex;
  gap: 10px;
}
</style>
